"""Unit tests for Scholar Tracker utilities."""

import pytest
import json
import os
import tempfile
from src.utils import Config, AuthorStats, PaperStats, DailyChanges, CitationChange


class TestConfig:
    """Tests for Config class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()
        assert config.author_id is None
        assert config.author_query is None
        assert config.max_retries == 3
        assert config.retry_delay == 5

    def test_config_from_values(self):
        """Test creating config from explicit values."""
        config = Config(
            author_id="test_id",
            author_query="Test Author",
            max_retries=5,
            retry_delay=10
        )
        assert config.author_id == "test_id"
        assert config.author_query == "Test Author"
        assert config.max_retries == 5
        assert config.retry_delay == 10

    def test_config_is_valid_with_id(self):
        """Test config validation with valid ID."""
        config = Config(author_id="VtK5lwUAAAAJ")
        assert config.is_valid() is True

    def test_config_is_valid_with_query(self):
        """Test config validation with valid query."""
        config = Config(author_query="John Doe University")
        assert config.is_valid() is True

    def test_config_invalid_default(self):
        """Test config validation with default placeholder."""
        config = Config(author_id="YOUR_SCHOLAR_ID_HERE")
        assert config.is_valid() is False

    def test_config_invalid_empty(self):
        """Test config validation with no values."""
        config = Config()
        assert config.is_valid() is False

    def test_config_from_file(self, tmp_path):
        """Test loading config from file."""
        config_file = tmp_path / "config.json"
        config_data = {
            "author_id": "test_id",
            "max_retries": 5
        }
        config_file.write_text(json.dumps(config_data))

        config = Config.from_file(str(config_file))
        assert config.author_id == "test_id"
        assert config.max_retries == 5
        assert config.retry_delay == 5  # default value

    def test_config_from_nonexistent_file(self, tmp_path, monkeypatch):
        """Test loading config from nonexistent file creates default."""
        config_file = tmp_path / "new_config.json"
        monkeypatch.chdir(tmp_path)

        config = Config.from_file(str(config_file))
        assert config_file.exists()
        assert config.author_id == "YOUR_SCHOLAR_ID_HERE"


class TestAuthorStats:
    """Tests for AuthorStats dataclass."""

    def test_author_stats_creation(self):
        """Test creating AuthorStats instance."""
        stats = AuthorStats(
            date="2024-01-01",
            total_citations=100,
            h_index=10,
            i10_index=5,
            papers=[
                PaperStats(title="Paper 1", citations=50, year="2023"),
                PaperStats(title="Paper 2", citations=30, year="2022")
            ]
        )
        assert stats.date == "2024-01-01"
        assert stats.total_citations == 100
        assert stats.h_index == 10
        assert len(stats.papers) == 2

    def test_author_stats_to_dict(self):
        """Test converting AuthorStats to dictionary."""
        stats = AuthorStats(
            date="2024-01-01",
            total_citations=100,
            h_index=10,
            i10_index=5,
            papers=[PaperStats(title="Paper 1", citations=50, year="2023")]
        )
        result = stats.to_dict()
        assert result["date"] == "2024-01-01"
        assert result["total_citations"] == 100
        assert len(result["papers"]) == 1
        assert result["papers"][0]["title"] == "Paper 1"

    def test_author_stats_from_dict(self):
        """Test creating AuthorStats from dictionary."""
        data = {
            "date": "2024-01-01",
            "total_citations": 100,
            "h_index": 10,
            "i10_index": 5,
            "papers": [
                {"title": "Paper 1", "citations": 50, "year": "2023"}
            ]
        }
        stats = AuthorStats.from_dict(data)
        assert stats.date == "2024-01-01"
        assert stats.total_citations == 100
        assert stats.papers[0].title == "Paper 1"


class TestDailyChanges:
    """Tests for DailyChanges dataclass."""

    def test_daily_changes_creation(self):
        """Test creating DailyChanges instance."""
        changes = DailyChanges(
            date="2024-01-01",
            total_citations_increase=10,
            papers_with_changes=[
                CitationChange(title="Paper 1", previous_citations=50, new_citations=55, increase=5),
                CitationChange(title="Paper 2", previous_citations=30, new_citations=35, increase=5)
            ]
        )
        assert changes.date == "2024-01-01"
        assert changes.total_citations_increase == 10
        assert len(changes.papers_with_changes) == 2

    def test_daily_changes_to_dict(self):
        """Test converting DailyChanges to dictionary."""
        changes = DailyChanges(
            date="2024-01-01",
            total_citations_increase=10,
            papers_with_changes=[
                CitationChange(title="Paper 1", previous_citations=50, new_citations=55, increase=5)
            ]
        )
        result = changes.to_dict()
        assert result["date"] == "2024-01-01"
        assert result["total_citations_increase"] == 10
        assert len(result["papers_with_changes"]) == 1


class TestPaperStats:
    """Tests for PaperStats dataclass."""

    def test_paper_stats_creation(self):
        """Test creating PaperStats instance."""
        paper = PaperStats(title="Test Paper", citations=42, year="2023")
        assert paper.title == "Test Paper"
        assert paper.citations == 42
        assert paper.year == "2023"
