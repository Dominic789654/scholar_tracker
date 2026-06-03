"""Unit tests for DashboardGenerator."""

import json

import pytest

from src.dashboard_generator import DashboardGenerator


def _history():
    return [
        {
            "date": "2024-01-01",
            "total_citations": 10,
            "h_index": 2,
            "i10_index": 1,
            "papers": [
                {"title": "Paper A", "citations": 7, "year": "2023"},
                {"title": "Paper B", "citations": 3, "year": "2024"},
            ],
        },
        {
            "date": "2024-01-01",
            "total_citations": 11,
            "h_index": 2,
            "i10_index": 1,
            "papers": [
                {"title": "Paper A", "citations": 8, "year": "2023"},
                {"title": "Paper B", "citations": 3, "year": "2024"},
            ],
        },
        {
            "date": "2024-01-02",
            "total_citations": 15,
            "h_index": 3,
            "i10_index": 1,
            "papers": [
                {"title": "Paper A", "citations": 10, "year": "2023"},
                {"title": "Paper B", "citations": 5, "year": "2024"},
            ],
        },
    ]


def test_generate_dashboard_embeds_summary_and_data(tmp_path):
    history_file = tmp_path / "citation_history.json"
    changes_file = tmp_path / "daily_changes.json"
    output_file = tmp_path / "dashboard.html"

    history_file.write_text(json.dumps(_history()))
    changes_file.write_text(
        json.dumps(
            [
                {
                    "date": "2024-01-02",
                    "total_citations_increase": 4,
                    "papers_with_changes": [
                        {
                            "title": "Paper A",
                            "previous_citations": 8,
                            "new_citations": 10,
                            "increase": 2,
                        }
                    ],
                }
            ]
        )
    )

    generator = DashboardGenerator(
        str(history_file),
        str(output_file),
        changes_file=str(changes_file),
    )

    assert generator.generate_dashboard() is True
    html = output_file.read_text()

    assert "Citation Dashboard" in html
    assert "15" in html
    assert "Paper A" in html
    assert '"samples": 2' in html
    assert '"total_citations": 15' in html


def test_build_payload_raises_without_history(tmp_path):
    history_file = tmp_path / "citation_history.json"
    output_file = tmp_path / "dashboard.html"
    history_file.write_text("[]")

    generator = DashboardGenerator(str(history_file), str(output_file))

    with pytest.raises(ValueError, match="No citation history"):
        generator.generate_dashboard()
