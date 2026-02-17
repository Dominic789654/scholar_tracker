"""Unit tests for ScholarTracker core functionality."""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.scholar_tracker import ScholarTracker


class TestScholarTrackerInit:
    """Tests for ScholarTracker initialization."""

    def test_init_with_author_id(self):
        """Test initialization with author ID."""
        tracker = ScholarTracker(author_id="test_id")
        assert tracker.author_id == "test_id"
        assert tracker.author_query is None

    def test_init_with_author_query(self):
        """Test initialization with author query."""
        tracker = ScholarTracker(author_query="John Doe")
        assert tracker.author_query == "John Doe"
        assert tracker.author_id is None

    def test_init_with_both(self):
        """Test initialization with both parameters."""
        tracker = ScholarTracker(author_id="test_id", author_query="John Doe")
        assert tracker.author_id == "test_id"
        assert tracker.author_query == "John Doe"

    def test_init_with_neither_raises(self):
        """Test initialization without parameters raises error."""
        with pytest.raises(ValueError, match="Either author_query or author_id"):
            ScholarTracker()

    def test_init_with_scraper_api_key(self):
        """Test initialization with ScraperAPI key."""
        tracker = ScholarTracker(author_id="test_id", scraper_api_key="test_key")
        assert tracker.scraper_api_key == "test_key"

    def test_init_scraper_api_key_from_env(self, monkeypatch):
        """Test ScraperAPI key loaded from environment."""
        monkeypatch.setenv("SCRAPER_API_KEY", "env_key")
        tracker = ScholarTracker(author_id="test_id")
        assert tracker.scraper_api_key == "env_key"


class TestScholarTrackerValidation:
    """Tests for stats validation."""

    @pytest.fixture
    def tracker(self):
        """Create a tracker instance for testing."""
        return ScholarTracker(author_id="test_id")

    def test_validate_valid_stats(self, tracker):
        """Test validation of valid stats."""
        stats = {
            "date": "2024-01-01",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        assert tracker._validate_stats(stats) is True

    def test_validate_negative_citations(self, tracker):
        """Test validation rejects negative citations."""
        stats = {
            "date": "2024-01-01",
            "total_citations": -10,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        assert tracker._validate_stats(stats) is False

    def test_validate_zero_h_index_with_high_citations(self, tracker):
        """Test validation rejects h_index=0 with high citations."""
        stats = {
            "date": "2024-01-01",
            "total_citations": 500,
            "h_index": 0,
            "i10_index": 10,
            "papers": [{"title": "Paper 1", "citations": 100, "year": "2023"}]
        }
        assert tracker._validate_stats(stats) is False

    def test_validate_empty_papers(self, tracker):
        """Test validation rejects empty papers list."""
        stats = {
            "date": "2024-01-01",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": []
        }
        assert tracker._validate_stats(stats) is False

    def test_validate_h_index_drop_from_previous(self, tracker):
        """Test validation rejects h_index dropping to 0."""
        stats = {
            "date": "2024-01-01",
            "total_citations": 100,
            "h_index": 0,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        previous = {
            "date": "2023-12-31",
            "total_citations": 90,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 45, "year": "2023"}]
        }
        assert tracker._validate_stats(stats, previous) is False

    def test_validate_accepts_normal_growth(self, tracker):
        """Test validation accepts normal citation growth."""
        stats = {
            "date": "2024-01-01",
            "total_citations": 110,
            "h_index": 6,
            "i10_index": 4,
            "papers": [{"title": "Paper 1", "citations": 55, "year": "2023"}]
        }
        previous = {
            "date": "2023-12-31",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        assert tracker._validate_stats(stats, previous) is True


class TestCitationChanges:
    """Tests for citation change calculation."""

    @pytest.fixture
    def tracker(self):
        """Create a tracker instance for testing."""
        return ScholarTracker(author_id="test_id")

    def test_calculate_changes_with_increase(self, tracker):
        """Test calculating citation increases."""
        current = {
            "date": "2024-01-01",
            "total_citations": 110,
            "h_index": 5,
            "i10_index": 3,
            "papers": [
                {"title": "Paper 1", "citations": 55, "year": "2023"},
                {"title": "Paper 2", "citations": 35, "year": "2022"}
            ]
        }
        previous = {
            "date": "2023-12-31",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": [
                {"title": "Paper 1", "citations": 50, "year": "2023"},
                {"title": "Paper 2", "citations": 30, "year": "2022"}
            ]
        }
        changes = tracker.get_citation_changes(current, previous)
        assert changes["total_citations_increase"] == 10
        assert len(changes["papers_with_changes"]) == 2
        assert changes["papers_with_changes"][0]["increase"] == 5

    def test_calculate_changes_no_changes(self, tracker):
        """Test calculating with no citation changes."""
        current = {
            "date": "2024-01-01",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        previous = {
            "date": "2023-12-31",
            "total_citations": 100,
            "h_index": 5,
            "i10_index": 3,
            "papers": [{"title": "Paper 1", "citations": 50, "year": "2023"}]
        }
        changes = tracker.get_citation_changes(current, previous)
        assert changes["total_citations_increase"] == 0
        assert len(changes["papers_with_changes"]) == 0

    def test_calculate_changes_none_inputs(self, tracker):
        """Test calculating with None inputs."""
        assert tracker.get_citation_changes(None, None) is None
        assert tracker.get_citation_changes({}, None) is None
        assert tracker.get_citation_changes(None, {}) is None
