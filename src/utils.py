"""Utility functions and classes for Scholar Tracker."""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


# User-Agent rotation to avoid detection
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


@dataclass
class Config:
    """Configuration for Scholar Tracker."""
    author_id: Optional[str] = None
    author_query: Optional[str] = None
    max_retries: int = 3
    retry_delay: int = 5
    scraper_api_key: Optional[str] = None

    @classmethod
    def from_file(cls, config_path: str = "config.json") -> 'Config':
        """Load configuration from JSON file."""
        default_config = {
            "author_id": "YOUR_SCHOLAR_ID_HERE",
            "author_query": None,
            "max_retries": 3,
            "retry_delay": 5
        }

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                # Add scraper_api_key from environment
                config["scraper_api_key"] = os.environ.get("SCRAPER_API_KEY")
                return cls(**config)
        else:
            # Create default config file
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {config_path}")
            print("Please update it with your Google Scholar ID")
            return cls()

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        if self.author_id == "YOUR_SCHOLAR_ID_HERE":
            return False
        return bool(self.author_id or self.author_query)


@dataclass
class PaperStats:
    """Statistics for a single paper."""
    title: str
    citations: int
    year: str


@dataclass
class AuthorStats:
    """Statistics for an author at a specific date."""
    date: str
    total_citations: int
    h_index: int
    i10_index: int
    papers: List[PaperStats] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "total_citations": self.total_citations,
            "h_index": self.h_index,
            "i10_index": self.i10_index,
            "papers": [
                {"title": p.title, "citations": p.citations, "year": p.year}
                for p in self.papers
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthorStats':
        """Create from dictionary."""
        return cls(
            date=data["date"],
            total_citations=data["total_citations"],
            h_index=data["h_index"],
            i10_index=data.get("i10_index", 0),
            papers=[
                PaperStats(title=p["title"], citations=p["citations"], year=p["year"])
                for p in data.get("papers", [])
            ]
        )


@dataclass
class CitationChange:
    """Citation changes for a single paper."""
    title: str
    previous_citations: int
    new_citations: int
    increase: int


@dataclass
class DailyChanges:
    """Daily citation changes."""
    date: str
    total_citations_increase: int
    papers_with_changes: List[CitationChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date,
            "total_citations_increase": self.total_citations_increase,
            "papers_with_changes": [
                {
                    "title": c.title,
                    "previous_citations": c.previous_citations,
                    "new_citations": c.new_citations,
                    "increase": c.increase
                }
                for c in self.papers_with_changes
            ]
        }


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
