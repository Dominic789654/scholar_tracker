"""Scholar Tracker - Core tracking functionality for Google Scholar citations."""

import json
import logging
import os
import random
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from scholarly import scholarly

try:
    from fp.fp import FreeProxy

    FREE_PROXY_AVAILABLE = True
except ImportError:
    FREE_PROXY_AVAILABLE = False
    logging.warning("free-proxy not installed, falling back to direct requests")

from .exceptions import (
    AuthorNotFoundError,
    DataFetchError,
    DataValidationError,
    RateLimitError,
    ScraperAPIError,
)
from .utils import USER_AGENTS

logger = logging.getLogger("scholar_tracker")
logger.setLevel(logging.INFO)

if not logger.handlers:
    os.makedirs("data", exist_ok=True)

    file_handler = RotatingFileHandler(
        "data/tracker.log",
        mode="a",
        maxBytes=1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(console_handler)

logging.basicConfig(level=logging.INFO, handlers=logger.handlers)


class ScholarTracker:
    """Tracker for Google Scholar citations."""

    def __init__(
        self,
        author_query: Optional[str] = None,
        author_id: Optional[str] = None,
        scraper_api_key: Optional[str] = None,
        use_free_proxy: bool = True,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        if not author_query and not author_id:
            raise ValueError("Either author_query or author_id must be provided.")

        self.author_query = author_query
        self.author_id = author_id
        self.scraper_api_key = scraper_api_key or os.environ.get("SCRAPER_API_KEY")
        self.use_free_proxy = use_free_proxy
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.data_file = "data/citation_history.json"
        self.daily_changes_file = "data/daily_changes.json"

        logger.info(
            "ScholarTracker initialized for author_query='%s', author_id='%s'",
            self.author_query,
            self.author_id,
        )
        if self.scraper_api_key:
            logger.info("ScraperAPI is configured for proxy support")
        if self.use_free_proxy and FREE_PROXY_AVAILABLE:
            logger.info("Free proxy support enabled")

    @staticmethod
    def _load_json_file(path: str, default: Any) -> Any:
        """Load JSON file or return default if it does not exist."""
        if not os.path.exists(path):
            return default
        with open(path, "r") as file:
            return json.load(file)

    @staticmethod
    def _save_json_file(path: str, data: Any) -> None:
        """Write JSON data to disk."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w") as file:
            json.dump(data, file, indent=2)

    @staticmethod
    def _paper_key(paper: Dict[str, Any]) -> Tuple[str, str]:
        """Return a stable key for paper matching across runs."""
        title = (paper.get("title") or "").strip().lower()
        year = str(paper.get("year") or "N/A").strip()
        return title, year

    @staticmethod
    def _parse_int(value: Any, default: int = 0) -> int:
        """Best-effort integer parsing."""
        try:
            if value is None:
                return default
            return int(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return default

    def _upsert_daily_change(self, changes: Dict[str, Any]) -> None:
        """Insert or replace daily change entry for a given date."""
        daily_changes = self._load_json_file(self.daily_changes_file, default=[])

        for index, entry in enumerate(daily_changes):
            if entry.get("date") == changes["date"]:
                daily_changes[index] = changes
                break
        else:
            daily_changes.append(changes)

        self._save_json_file(self.daily_changes_file, daily_changes)
        logger.info("Saved daily changes to %s", self.daily_changes_file)

    def _get_free_proxy(self) -> Optional[str]:
        """Get a free proxy using free-proxy library."""
        if not FREE_PROXY_AVAILABLE:
            return None

        try:
            proxy = FreeProxy(timeout=1, rand=True).get()
            if proxy:
                logger.info("Got free proxy: %s", proxy)
                return proxy
        except Exception as exc:
            logger.warning("Failed to get free proxy: %s", exc)
        return None

    def _make_request(
        self,
        url: str,
        use_scraper_api: bool = False,
        use_free_proxy: bool = True,
    ) -> requests.Response:
        """Make HTTP request - try direct first, then free proxy if fails."""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if use_scraper_api and self.scraper_api_key:
            return requests.get(
                "http://api.scraperapi.com",
                params={
                    "api_key": self.scraper_api_key,
                    "url": url,
                    "render": "false",
                },
                headers=headers,
                timeout=60,
            )

        try:
            logger.info("Trying direct request first...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response
        except Exception as direct_error:
            logger.warning("Direct request failed: %s", direct_error)

            if self.use_free_proxy and use_free_proxy and FREE_PROXY_AVAILABLE:
                free_proxy = self._get_free_proxy()
                if free_proxy:
                    try:
                        logger.info("Trying with free proxy: %s", free_proxy)
                        proxies = {"http": free_proxy, "https": free_proxy}
                        response = requests.get(
                            url,
                            headers=headers,
                            proxies=proxies,
                            timeout=30,
                        )
                        response.raise_for_status()
                        return response
                    except Exception as proxy_error:
                        logger.warning("Free proxy also failed: %s", proxy_error)

            raise direct_error

    def _manual_fetch_author_data(self, author_id: str) -> Optional[Dict[str, Any]]:
        """Manually fetch author data from Google Scholar when scholarly fails."""
        try:
            url = (
                "https://scholar.google.com/citations?hl=en"
                f"&user={author_id}&pagesize=100&view_op=list_works&sortby=pubdate"
            )
            logger.info("Manually fetching data from: %s", url)
            response = None

            if self.scraper_api_key:
                logger.info("Attempting fetch via ScraperAPI...")
                try:
                    response = self._make_request(url, use_scraper_api=True)
                    if response.status_code == 200:
                        logger.info("ScraperAPI fetch successful")
                    elif response.status_code == 403:
                        raise ScraperAPIError("ScraperAPI returned 403 Forbidden", status_code=403)
                    else:
                        raise ScraperAPIError(
                            f"ScraperAPI returned status {response.status_code}",
                            status_code=response.status_code,
                        )
                except ScraperAPIError as exc:
                    logger.warning("ScraperAPI failed: %s, trying direct request...", exc)
                    response = None
                except Exception as exc:
                    logger.warning("ScraperAPI failed: %s, trying direct request...", exc)
                    response = None

            if response is None:
                logger.info("Attempting fetch with automatic fallback (direct -> free proxy)...")
                response = self._make_request(url, use_scraper_api=False, use_free_proxy=True)

            if response.status_code == 403:
                raise DataFetchError(
                    "Access denied by Google Scholar (403). Try using ScraperAPI.",
                    status_code=403,
                    retryable=True,
                )
            if response.status_code == 404:
                raise AuthorNotFoundError(author_id=author_id)
            if response.status_code == 429:
                raise RateLimitError("Rate limited by Google Scholar")
            if response.status_code >= 500:
                raise DataFetchError(
                    f"Server error from Google Scholar ({response.status_code})",
                    status_code=response.status_code,
                    retryable=True,
                )

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            name_tag = soup.find("div", id="gsc_prf_in")
            name = name_tag.get_text(strip=True) if name_tag else "Unknown"

            stats_table = soup.find("table", id="gsc_rsb_st")
            citations = 0
            hindex = 0
            i10index = 0
            if stats_table:
                rows = stats_table.find_all("tr")
                if len(rows) >= 2:
                    cols = rows[1].find_all("td")
                    if len(cols) >= 2:
                        citations = self._parse_int(cols[1].get_text(strip=True))
                if len(rows) >= 3:
                    cols = rows[2].find_all("td")
                    if len(cols) >= 2:
                        hindex = self._parse_int(cols[1].get_text(strip=True))
                if len(rows) >= 4:
                    cols = rows[3].find_all("td")
                    if len(cols) >= 2:
                        i10index = self._parse_int(cols[1].get_text(strip=True))

            publications = []
            for row in soup.find_all("tr", class_="gsc_a_tr"):
                title_tag = row.find("a", class_="gsc_a_at")
                year_container = row.find("td", class_="gsc_a_y")
                if year_container is None:
                    year_container = row.find("span", class_="gsc_a_h gsc_a_hc gs_ibl")
                cited_tag = row.find("a", class_="gsc_a_ac")
                if cited_tag is None:
                    cited_tag = row.find("a", class_="gsc_a_ac gs_ibl")

                if not title_tag:
                    continue

                title = title_tag.get_text(strip=True)
                year = "N/A"
                if year_container:
                    year_text = year_container.get_text(strip=True)
                    year = year_text or "N/A"

                publications.append(
                    {
                        "bib": {"title": title, "pub_year": year},
                        "num_citations": self._parse_int(
                            cited_tag.get_text(strip=True) if cited_tag else 0
                        ),
                    }
                )

            author_data = {
                "name": name,
                "citedby": citations,
                "hindex": hindex,
                "i10index": i10index,
                "publications": publications,
            }

            logger.info(
                "Successfully manually fetched data for %s: %s citations, %s papers",
                name,
                citations,
                len(publications),
            )
            return author_data
        except (AuthorNotFoundError, RateLimitError, DataFetchError):
            raise
        except Exception as exc:
            logger.error("Manual fetch failed: %s", exc)
            raise DataFetchError(f"Manual fetch failed: {exc}", retryable=True) from exc

    def get_author_stats(
        self,
        max_retries: Optional[int] = None,
        retry_delay: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve author statistics from Google Scholar with retry logic."""
        max_retries = max_retries if max_retries is not None else self.max_retries
        retry_delay = retry_delay if retry_delay is not None else self.retry_delay
        last_error = None

        for attempt in range(max_retries):
            try:
                author = None
                if self.author_id:
                    logger.info(
                        "Searching for author by ID: '%s' (attempt %s/%s)",
                        self.author_id,
                        attempt + 1,
                        max_retries,
                    )
                    if self.scraper_api_key:
                        logger.info("ScraperAPI key detected, using manual fetch path first")
                        author = self._manual_fetch_author_data(self.author_id)
                    else:
                        author = scholarly.search_author_id(self.author_id)
                        if author:
                            try:
                                author = scholarly.fill(
                                    author,
                                    sections=["basics", "indices", "publications"],
                                )
                            except Exception as fill_error:
                                logger.warning(
                                    "Could not fill author details, using manual fetch: %s",
                                    fill_error,
                                )
                                author = self._manual_fetch_author_data(self.author_id)
                else:
                    logger.info(
                        "Searching for author by name: '%s' (attempt %s/%s)",
                        self.author_query,
                        attempt + 1,
                        max_retries,
                    )
                    search_query = scholarly.search_author(self.author_query)
                    author = next(search_query)
                    try:
                        author = scholarly.fill(
                            author,
                            sections=["basics", "indices", "publications"],
                        )
                    except Exception as fill_error:
                        logger.warning("Could not fill author details: %s", fill_error)
                        raise AuthorNotFoundError(author_query=self.author_query)

                if not author:
                    logger.error(
                        "Could not find author with ID '%s' or query '%s'.",
                        self.author_id,
                        self.author_query,
                    )
                    raise AuthorNotFoundError(
                        author_id=self.author_id,
                        author_query=self.author_query,
                    )

                logger.info("Found author: %s", author.get("name", "Unknown"))
                today = datetime.now().strftime("%Y-%m-%d")

                stats = {
                    "date": today,
                    "total_citations": author.get("citedby", 0),
                    "h_index": author.get("hindex", 0),
                    "i10_index": author.get("i10index", 0),
                    "papers": [],
                }

                for publication in author.get("publications", []):
                    bibliography = publication.get("bib", {})
                    paper = {
                        "title": bibliography.get("title"),
                        "citations": publication.get("num_citations", 0),
                        "year": bibliography.get("pub_year", "N/A"),
                    }
                    stats["papers"].append(paper)

                logger.info("Successfully collected stats for %s papers.", len(stats["papers"]))

                if not self._validate_stats(stats, previous_stats=None):
                    logger.error("Stats validation failed, returning None")
                    raise DataValidationError("Stats validation failed")

                return stats
            except AuthorNotFoundError as exc:
                logger.error("Author not found: %s", exc.message)
                return None
            except RateLimitError as exc:
                logger.warning("Rate limited: %s", exc.message)
                last_error = exc
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** (attempt + 2))
                    logger.info("Retrying in %s seconds...", wait_time)
                    time.sleep(wait_time)
            except DataFetchError as exc:
                logger.error(
                    "Data fetch error (attempt %s/%s): %s",
                    attempt + 1,
                    max_retries,
                    exc.message,
                )
                last_error = exc
                if exc.retryable and attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    logger.info("Retrying in %s seconds...", wait_time)
                    time.sleep(wait_time)
                elif not exc.retryable:
                    return None
            except Exception as exc:
                logger.error("Unexpected error (attempt %s/%s): %s", attempt + 1, max_retries, exc)
                last_error = exc
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2**attempt)
                    logger.info("Retrying in %s seconds...", wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error("Failed after %s attempts", max_retries, exc_info=True)
                    return None

        logger.error("All retry attempts failed. Last error: %s", last_error)
        return None

    def get_citation_changes(
        self,
        current_stats: Dict[str, Any],
        previous_stats: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Compare current and previous stats to find citation changes."""
        if not previous_stats or not current_stats:
            return None

        logger.info("Calculating citation changes...")
        changes = {
            "date": current_stats["date"],
            "total_citations_increase": current_stats["total_citations"]
            - previous_stats["total_citations"],
            "papers_with_changes": [],
        }

        previous_citations = {
            self._paper_key(paper): paper["citations"] for paper in previous_stats["papers"]
        }

        for paper in current_stats["papers"]:
            previous_count = previous_citations.get(self._paper_key(paper), 0)
            if paper["citations"] > previous_count:
                changes["papers_with_changes"].append(
                    {
                        "title": paper["title"],
                        "previous_citations": previous_count,
                        "new_citations": paper["citations"],
                        "increase": paper["citations"] - previous_count,
                    }
                )

        changes["papers_with_changes"].sort(
            key=lambda item: (-item["increase"], item["title"].lower())
        )

        if changes["papers_with_changes"]:
            logger.info(
                "Found %s papers with new citations.",
                len(changes["papers_with_changes"]),
            )
        else:
            logger.info("No new citations found for any papers.")

        return changes

    def _validate_stats(
        self,
        stats: Dict[str, Any],
        previous_stats: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate collected stats to prevent saving invalid data."""
        logger.info("Validating collected stats...")

        if stats["total_citations"] < 0:
            logger.error("Invalid total_citations: %s", stats["total_citations"])
            return False
        if stats["h_index"] < 0:
            logger.error("Invalid h_index: %s", stats["h_index"])
            return False
        if stats.get("i10_index", 0) < 0:
            logger.error("Invalid i10_index: %s", stats["i10_index"])
            return False
        if not stats["papers"]:
            logger.error("No papers found in stats")
            return False

        if stats["total_citations"] > 100 and stats["h_index"] == 0:
            logger.error(
                "Inconsistent stats: %s citations but h_index=0",
                stats["total_citations"],
            )
            return False

        if previous_stats:
            if stats["total_citations"] < previous_stats["total_citations"] - 5:
                logger.warning(
                    "Unusual citation drop: %s -> %s",
                    previous_stats["total_citations"],
                    stats["total_citations"],
                )

            if previous_stats["h_index"] > 0 and stats["h_index"] == 0:
                logger.error(
                    "h_index dropped from %s to 0 - likely parsing error",
                    previous_stats["h_index"],
                )
                return False

        logger.info("Stats validation passed")
        return True

    def update_history(self) -> bool:
        """Update citation history with new data."""
        logger.info("Starting history update...")
        stats = self.get_author_stats(
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
        )
        if not stats:
            logger.warning("Aborting history update because fetching stats failed.")
            return False

        history = self._load_json_file(self.data_file, default=[])
        if history:
            logger.info("Loaded %s history entries from %s", len(history), self.data_file)
        else:
            logger.info("No history file found. A new one will be created.")

        existing_today = bool(history and history[-1]["date"] == stats["date"])
        previous_stats = None
        if existing_today and len(history) > 1:
            previous_stats = history[-2]
        elif not existing_today and history:
            previous_stats = history[-1]

        if not self._validate_stats(stats, previous_stats):
            logger.error("Stats validation failed, aborting update")
            return False

        if existing_today and history[-1] == stats:
            logger.info("Today's data is unchanged. Skipping history rewrite.")
        elif existing_today:
            logger.info("Refreshing existing entry for %s.", stats["date"])
            history[-1] = stats
            self._save_json_file(self.data_file, history)
        else:
            history.append(stats)
            self._save_json_file(self.data_file, history)
            logger.info("Appended new history entry for %s.", stats["date"])

        if previous_stats:
            changes = self.get_citation_changes(stats, previous_stats)
            if changes:
                self._upsert_daily_change(changes)
        else:
            logger.info("No previous stats to compare against.")

        logger.info("History update complete.")
        return True
