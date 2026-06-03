"""Unit tests for ChartGenerator."""

import json
from pathlib import Path

import plotly.graph_objects as go

from src.chart_generator import ChartGenerator


def _sample_history():
    return [
        {
            "date": "2024-01-01",
            "total_citations": 10,
            "h_index": 2,
            "i10_index": 1,
            "papers": [
                {"title": "Paper 1", "citations": 10, "year": "2023"},
                {"title": "Paper 2", "citations": 4, "year": "2022"},
            ],
        },
        {
            "date": "2024-01-02",
            "total_citations": 12,
            "h_index": 2,
            "i10_index": 1,
            "papers": [
                {"title": "Paper 1", "citations": 11, "year": "2023"},
                {"title": "Paper 2", "citations": 5, "year": "2022"},
            ],
        },
    ]


def test_generate_charts_writes_outputs_and_cache(tmp_path, monkeypatch):
    """Chart generation should write both chart families and update cache metadata."""
    history = _sample_history()
    data_file = tmp_path / "citation_history.json"
    data_file.write_text(json.dumps(history))

    def fake_write_html(self, path, *args, **kwargs):
        del self, args, kwargs
        Path(path).write_text("<html>chart</html>")

    def fake_write_image(self, path, *args, **kwargs):
        del self, args, kwargs
        Path(path).write_text("image")

    monkeypatch.setattr(go.Figure, "write_html", fake_write_html)
    monkeypatch.setattr(go.Figure, "write_image", fake_write_image)

    chart_generator = ChartGenerator(str(data_file), str(tmp_path))
    chart_generator.generate_charts(force=True)

    assert (tmp_path / "citation_trends.html").exists()
    assert (tmp_path / "citation_trends.png").exists()
    assert (tmp_path / "paper_trends.html").exists()
    assert (tmp_path / "paper_trends.png").exists()

    cache = json.loads((tmp_path / ".chart_cache.json").read_text())
    expected_hash = chart_generator._get_data_hash(history)
    assert cache["citation_trends_hash"] == expected_hash
    assert cache["paper_trends_hash"] == expected_hash
    assert "citation_trends_date" in cache
    assert "paper_trends_date" in cache


def test_generate_charts_skips_when_cache_is_current(tmp_path, monkeypatch):
    """Existing outputs with matching cache hashes should avoid regeneration."""
    history = _sample_history()
    data_file = tmp_path / "citation_history.json"
    data_file.write_text(json.dumps(history))

    chart_generator = ChartGenerator(str(data_file), str(tmp_path))
    current_hash = chart_generator._get_data_hash(history)
    (tmp_path / ".chart_cache.json").write_text(
        json.dumps(
            {
                "citation_trends_hash": current_hash,
                "paper_trends_hash": current_hash,
            }
        )
    )
    for output_name in (
        "citation_trends.html",
        "citation_trends.png",
        "paper_trends.html",
        "paper_trends.png",
    ):
        (tmp_path / output_name).write_text("existing output")

    def fail_generation(*args, **kwargs):
        del args, kwargs
        raise AssertionError("chart should not be regenerated")

    monkeypatch.setattr(ChartGenerator, "_generate_citation_trends", fail_generation)
    monkeypatch.setattr(ChartGenerator, "generate_paper_trends", fail_generation)

    chart_generator.generate_charts()
