import logging
from logging.handlers import RotatingFileHandler
from scholarly import scholarly
from datetime import datetime
import json
import os
import time
import requests
from bs4 import BeautifulSoup
import re

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
    def __init__(self, author_query=None, author_id=None):
        if not author_query and not author_id:
            raise ValueError("Either author_query or author_id must be provided.")
        self.author_query = author_query
        self.author_id = author_id
        self.data_file = "data/citation_history.json"
        self.daily_changes_file = "data/daily_changes.json"
        logging.info(f"ScholarTracker initialized for author_query: '{self.author_query}', author_id: '{self.author_id}'")
    
    def _manual_fetch_author_data(self, author_id):
        """Manually fetch author data from Google Scholar when scholarly fails"""
        try:
            url = f"https://scholar.google.com/citations?hl=en&user={author_id}&pagesize=100&view_op=list_works&sortby=pubdate"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            logging.info(f"Manually fetching data from: {url}")
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract author name
            name_tag = soup.find('div', id='gsc_prf_in')
            name = name_tag.text if name_tag else 'Unknown'
            
            # Extract citation stats
            stats_table = soup.find('table', id='gsc_rsb_st')
            citations = 0
            hindex = 0
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
                'publications': publications
            }
            
            logging.info(f"Successfully manually fetched data for {name}: {citations} citations, {len(publications)} papers")
            return author_data
            
        except Exception as e:
            logging.error(f"Manual fetch failed: {e}")
            return None
        
    def get_author_stats(self, max_retries=3, retry_delay=5):
        """Retrieve author statistics from Google Scholar with retry logic"""
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
                            author = scholarly.fill(author, sections=['basics', 'publications'])
                        except Exception as fill_error:
                            logging.warning(f"Could not fill author details, using basic info: {fill_error}")
                            # If fill fails, try to get data manually from the author page
                            author = self._manual_fetch_author_data(self.author_id)
                else:
                    logging.info(f"Searching for author by name: '{self.author_query}' (attempt {attempt + 1}/{max_retries})")
                    search_query = scholarly.search_author(self.author_query)
                    author = next(search_query)
                    try:
                        author = scholarly.fill(author, sections=['basics', 'publications'])
                    except Exception as fill_error:
                        logging.warning(f"Could not fill author details: {fill_error}")
                        return None
                
                if not author:
                    logging.error(f"Could not find author with ID '{self.author_id}' or query '{self.author_query}'.")
                    return None

                logging.info(f"Found author: {author.get('name', 'Unknown')}")
                
                # Get current date
                today = datetime.now().strftime("%Y-%m-%d")
                
                # Collect stats
                stats = {
                    "date": today,
                    "total_citations": author.get('citedby', 0),
                    "h_index": author.get('hindex', 0),
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
                return stats
                
            except StopIteration:
                logging.error(f"Author with query '{self.author_query}' not found on Google Scholar.")
                return None
            except Exception as e:
                logging.error(f"Error fetching scholar data (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Failed after {max_retries} attempts", exc_info=True)
                    return None
    
    def get_citation_changes(self, current_stats, previous_stats):
        """Compare current and previous stats to find citation changes"""
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
            
    def update_history(self):
        """Update citation history with new data"""
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

        # Get previous day's stats
        previous_stats = history[-1] if history else None
        
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