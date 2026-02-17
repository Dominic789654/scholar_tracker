"""Scholar Tracker - Core tracking functionality for Google Scholar citations."""

import logging
from logging.handlers import RotatingFileHandler
from scholarly import scholarly
from datetime import datetime
import json
import os
import time
import requests
from bs4 import BeautifulSoup
import random
from typing import Optional, List, Dict, Any

from .utils import USER_AGENTS, AuthorStats, PaperStats, DailyChanges, CitationChange
from .exceptions import (
    ScholarTrackerError,
    ConfigurationError,
    DataFetchError,
    DataValidationError,
    RateLimitError,
    AuthorNotFoundError,
    ScraperAPIError,
)

# Configure logging with rotation (max 1MB per file, keep 3 backups)
logger = logging.getLogger('scholar_tracker')
logger.setLevel(logging.INFO)

# Prevent duplicate handlers
if not logger.handlers:
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        "data/tracker.log",
        mode='a',
        maxBytes=1024*1024,  # 1MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

# Set as global logger
logging.basicConfig(level=logging.INFO, handlers=logger.handlers)


class ScholarTracker:
    """Tracker for Google Scholar citations."""

    def __init__(
        self,
        author_query: Optional[str] = None,
        author_id: Optional[str] = None,
        scraper_api_key: Optional[str] = None
    ):
        if not author_query and not author_id:
            raise ValueError("Either author_query or author_id must be provided.")
        self.author_query = author_query
        self.author_id = author_id
        self.scraper_api_key = scraper_api_key or os.environ.get('SCRAPER_API_KEY')
        self.data_file = "data/citation_history.json"
        self.daily_changes_file = "data/daily_changes.json"
        logging.info(f"ScholarTracker initialized for author_query: '{self.author_query}', author_id: '{self.author_id}'")
        if self.scraper_api_key:
            logging.info("ScraperAPI is configured for proxy support")

    def _get_scraper_api_url(self, url: str) -> Optional[str]:
        """Get ScraperAPI proxy URL if API key is available."""
        if not self.scraper_api_key:
            return None
        return f"http://scraperapi:{self.scraper_api_key}@proxy-server.scraperapi.com:8001"

    def _make_request(self, url: str, use_scraper_api: bool = False) -> requests.Response:
        """Make HTTP request with optional ScraperAPI proxy."""
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        if use_scraper_api and self.scraper_api_key:
            # Use ScraperAPI proxy
            proxies = {
                'http': self._get_scraper_api_url(url),
                'https': self._get_scraper_api_url(url),
            }
            # ScraperAPI handles headers internally, but we can pass custom headers
            response = requests.get(
                'http://api.scraperapi.com',
                params={
                    'api_key': self.scraper_api_key,
                    'url': url,
                    'render': 'false'
                },
                timeout=60
            )
        else:
            response = requests.get(url, headers=headers, timeout=30)

        return response

    def _manual_fetch_author_data(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Manually fetch author data from Google Scholar when scholarly fails."""
        try:
            url = f"https://scholar.google.com/citations?hl=en&user={author_id}&pagesize=100&view_op=list_works&sortby=pubdate"
            logging.info(f"Manually fetching data from: {url}")
            response = None

            # Try ScraperAPI first if available
            if self.scraper_api_key:
                logging.info("Attempting fetch via ScraperAPI...")
                try:
                    response = self._make_request(url, use_scraper_api=True)
                    if response.status_code == 200 and 'scholar.google.com' in response.url:
                        logging.info("ScraperAPI fetch successful")
                    elif response.status_code == 403:
                        raise ScraperAPIError("ScraperAPI returned 403 Forbidden", status_code=403)
                    else:
                        logging.warning(f"ScraperAPI returned status {response.status_code}, falling back to direct request")
                        raise ScraperAPIError(f"ScraperAPI returned status {response.status_code}", status_code=response.status_code)
                except ScraperAPIError:
                    raise
                except Exception as e:
                    logging.warning(f"ScraperAPI failed: {e}, trying direct request...")
                    response = None

            # Fallback to direct request
            if response is None:
                logging.info("Attempting direct fetch...")
                headers = {
                    'User-Agent': random.choice(USER_AGENTS),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
                response = requests.get(url, headers=headers, timeout=30)

            # Handle response errors
            if response.status_code == 403:
                raise DataFetchError(
                    f"Access denied by Google Scholar (403). Try using ScraperAPI.",
                    status_code=403,
                    retryable=True
                )
            elif response.status_code == 404:
                raise AuthorNotFoundError(author_id=author_id)
            elif response.status_code == 429:
                raise RateLimitError("Rate limited by Google Scholar")
            elif response.status_code >= 500:
                raise DataFetchError(
                    f"Server error from Google Scholar ({response.status_code})",
                    status_code=response.status_code,
                    retryable=True
                )

            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract author name
            name_tag = soup.find('div', id='gsc_prf_in')
            name = name_tag.text if name_tag else 'Unknown'
            
            # Extract citation stats
            stats_table = soup.find('table', id='gsc_rsb_st')
            citations = 0
            hindex = 0
            i10index = 0
            if stats_table:
                rows = stats_table.find_all('tr')
                if len(rows) >= 2:
                    cols = rows[1].find_all('td')
                    if len(cols) >= 2:
                        citations = int(cols[1].text.strip())
                if len(rows) >= 3:
                    cols = rows[2].find_all('td')
                    if len(cols) >= 2:
                        hindex = int(cols[1].text.strip())
                if len(rows) >= 4:
                    cols = rows[3].find_all('td')
                    if len(cols) >= 2:
                        i10index = int(cols[1].text.strip())
            
            # Extract publications
            publications = []
            pub_rows = soup.find_all('tr', class_='gsc_a_tr')
            for row in pub_rows:
                title_tag = row.find('a', class_='gsc_a_at')
                year_tag = row.find('span', class_='gsc_a_h gsc_a_hc gs_ibl')
                cited_tag = row.find('a', class_='gsc_a_ac gs_ibl')
                
                if title_tag:
                    title = title_tag.text
                    year = year_tag.text if year_tag else 'N/A'
                    cited = cited_tag.text if cited_tag and cited_tag.text else '0'
                    try:
                        cited_count = int(cited) if cited.isdigit() else 0
                    except:
                        cited_count = 0
                    
                    publications.append({
                        'bib': {'title': title, 'pub_year': year},
                        'num_citations': cited_count
                    })
            
            author_data = {
                'name': name,
                'citedby': citations,
                'hindex': hindex,
                'i10index': i10index,
                'publications': publications
            }
            
            logging.info(f"Successfully manually fetched data for {name}: {citations} citations, {len(publications)} papers")
            return author_data
            
        except Exception as e:
            logging.error(f"Manual fetch failed: {e}")
            return None
        
    def get_author_stats(
        self,
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Optional[Dict[str, Any]]:
        """Retrieve author statistics from Google Scholar with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                author = None
                if self.author_id:
                    logging.info(f"Searching for author by ID: '{self.author_id}' (attempt {attempt + 1}/{max_retries})")
                    # First get basic author info without filling
                    author = scholarly.search_author_id(self.author_id)
                    if author:
                        # Then try to fill with publications
                        try:
                            author = scholarly.fill(author, sections=['basics', 'indices', 'publications'])
                        except Exception as fill_error:
                            logging.warning(f"Could not fill author details, using manual fetch: {fill_error}")
                            # If fill fails, try to get data manually from the author page
                            author = self._manual_fetch_author_data(self.author_id)
                else:
                    logging.info(f"Searching for author by name: '{self.author_query}' (attempt {attempt + 1}/{max_retries})")
                    search_query = scholarly.search_author(self.author_query)
                    author = next(search_query)
                    try:
                        author = scholarly.fill(author, sections=['basics', 'indices', 'publications'])
                    except Exception as fill_error:
                        logging.warning(f"Could not fill author details: {fill_error}")
                        raise AuthorNotFoundError(author_query=self.author_query)

                if not author:
                    logging.error(f"Could not find author with ID '{self.author_id}' or query '{self.author_query}'.")
                    raise AuthorNotFoundError(author_id=self.author_id, author_query=self.author_query)

                logging.info(f"Found author: {author.get('name', 'Unknown')}")

                # Get current date
                today = datetime.now().strftime("%Y-%m-%d")

                # Collect stats
                stats = {
                    "date": today,
                    "total_citations": author.get('citedby', 0),
                    "h_index": author.get('hindex', 0),
                    "i10_index": author.get('i10index', 0),
                    "papers": []
                }

                # Collect individual paper stats
                for pub in author.get('publications', []):
                    # The 'bib' key may not exist for all publications, so we use .get()
                    bib = pub.get('bib', {})
                    paper = {
                        "title": bib.get('title'),
                        "citations": pub.get('num_citations', 0),
                        "year": bib.get('pub_year', 'N/A')
                    }
                    stats["papers"].append(paper)
                    
                logging.info(f"Successfully collected stats for {len(stats['papers'])} papers.")

                # Validate the collected stats
                if not self._validate_stats(stats, previous_stats=None):
                    logging.error("Stats validation failed, returning None")
                    raise DataValidationError("Stats validation failed")

                return stats

            except AuthorNotFoundError as e:
                logging.error(f"Author not found: {e.message}")
                return None  # Don't retry for author not found
            except RateLimitError as e:
                logging.warning(f"Rate limited: {e.message}")
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** (attempt + 2))  # Longer wait for rate limits
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
            except DataFetchError as e:
                logging.error(f"Data fetch error (attempt {attempt + 1}/{max_retries}): {e.message}")
                last_error = e
                if e.retryable and attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                elif not e.retryable:
                    return None  # Don't retry non-retryable errors
            except Exception as e:
                logging.error(f"Unexpected error (attempt {attempt + 1}/{max_retries}): {e}")
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Failed after {max_retries} attempts", exc_info=True)
                    return None

        logging.error(f"All retry attempts failed. Last error: {last_error}")
        return None
    
    def get_citation_changes(
        self,
        current_stats: Dict[str, Any],
        previous_stats: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Compare current and previous stats to find citation changes."""
        if not previous_stats or not current_stats:
            return None

        logging.info("Calculating citation changes...")
        changes = {
            "date": current_stats["date"],
            "total_citations_increase": current_stats["total_citations"] - previous_stats["total_citations"],
            "papers_with_changes": []
        }
        
        # Create a map of previous paper citations
        prev_citations = {paper["title"]: paper["citations"] for paper in previous_stats["papers"]}
        
        # Check each current paper for changes
        for paper in current_stats["papers"]:
            prev_count = prev_citations.get(paper["title"], 0)
            if paper["citations"] > prev_count:
                changes["papers_with_changes"].append({
                    "title": paper["title"],
                    "previous_citations": prev_count,
                    "new_citations": paper["citations"],
                    "increase": paper["citations"] - prev_count
                })
        
        if changes["papers_with_changes"]:
            logging.info(f"Found {len(changes['papers_with_changes'])} papers with new citations.")
        else:
            logging.info("No new citations found for any papers.")

        return changes

    def _validate_stats(
        self,
        stats: Dict[str, Any],
        previous_stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Validate collected stats to prevent saving invalid data.
        
        Checks:
        - h_index should not be 0 if total_citations > 0 (unless first entry)
        - total_citations should be non-negative
        - h_index should be non-negative
        - i10_index should be non-negative
        - papers list should not be empty
        """
        logging.info("Validating collected stats...")
        
        # Basic non-negative checks
        if stats["total_citations"] < 0:
            logging.error(f"Invalid total_citations: {stats['total_citations']}")
            return False
            
        if stats["h_index"] < 0:
            logging.error(f"Invalid h_index: {stats['h_index']}")
            return False
            
        if stats.get("i10_index", 0) < 0:
            logging.error(f"Invalid i10_index: {stats['i10_index']}")
            return False
        
        # Check for empty papers list
        if not stats["papers"]:
            logging.error("No papers found in stats")
            return False
        
        # Check h_index consistency - if we have citations but h_index is 0, something is wrong
        # Skip this check if it's the first entry (no previous stats to compare)
        if stats["total_citations"] > 100 and stats["h_index"] == 0:
            logging.error(f"Inconsistent stats: {stats['total_citations']} citations but h_index=0")
            return False
        
        # Compare with previous stats if available
        if previous_stats:
            # Citations should generally not decrease
            if stats["total_citations"] < previous_stats["total_citations"] - 5:
                # Allow small variance due to Google Scholar corrections, but flag large drops
                logging.warning(
                    f"Unusual citation drop: {previous_stats['total_citations']} -> {stats['total_citations']}"
                )
            
            # h_index should not decrease significantly
            if previous_stats["h_index"] > 0 and stats["h_index"] == 0:
                logging.error(f"h_index dropped from {previous_stats['h_index']} to 0 - likely parsing error")
                return False
        
        logging.info("Stats validation passed")
        return True

    def update_history(self) -> bool:
        """Update citation history with new data."""
        logging.info("Starting history update...")
        stats = self.get_author_stats()
        if not stats:
            logging.warning("Aborting history update because fetching stats failed.")
            return False

        # Load existing history
        history = []
        if os.path.exists(self.data_file):
            logging.info(f"Loading existing history from {self.data_file}")
            with open(self.data_file, 'r') as f:
                history = json.load(f)
        else:
            logging.info("No history file found. A new one will be created.")

        # Check if we already have an entry for today
        if history and history[-1]["date"] == stats["date"]:
            logging.info(f"Already have data for {stats['date']}. Skipping duplicate entry.")
            return True

        # Get previous day's stats
        previous_stats = history[-1] if history else None

        # Validate stats against previous data
        if not self._validate_stats(stats, previous_stats):
            logging.error("Stats validation failed, aborting update")
            return False

        # Calculate citation changes
        if previous_stats:
            logging.info("Comparing with previous stats to find citation changes.")
            changes = self.get_citation_changes(stats, previous_stats)
            if changes and changes["papers_with_changes"]:
                logging.info("Changes found, updating daily changes file.")
                # Load existing changes
                daily_changes = []
                if os.path.exists(self.daily_changes_file):
                    with open(self.daily_changes_file, 'r') as f:
                        daily_changes = json.load(f)
                
                # Add new changes
                daily_changes.append(changes)
                
                # Save updated changes
                os.makedirs(os.path.dirname(self.daily_changes_file), exist_ok=True)
                with open(self.daily_changes_file, 'w') as f:
                    json.dump(daily_changes, f, indent=2)
                logging.info(f"Saved daily changes to {self.daily_changes_file}")
        else:
            logging.info("No previous stats to compare against.")

        # Add new stats to history
        history.append(stats)
        
        # Save updated history
        logging.info(f"Saving updated history to {self.data_file}")
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        logging.info("History update complete.")
        return True