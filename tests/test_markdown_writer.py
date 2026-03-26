"""Unit tests for MarkdownWriter."""

import json

from src.markdown_writer import MarkdownWriter


class TestMarkdownWriter:
    def test_generate_markdown_escapes_pipe_characters(self, tmp_path):
        data_file = tmp_path / "citation_history.json"
        output_file = tmp_path / "citations.md"
        daily_changes_file = tmp_path / "daily_changes.json"

        history = [
            {
                "date": "2024-01-02",
                "total_citations": 10,
                "h_index": 2,
                "i10_index": 1,
                "papers": [
                    {"title": "Paper | One", "citations": 10, "year": "2024"},
                ],
            }
        ]
        changes = [
            {
                "date": "2024-01-02",
                "total_citations_increase": 0,
                "papers_with_changes": [],
            }
        ]

        data_file.write_text(json.dumps(history))
        daily_changes_file.write_text(json.dumps(changes))

        writer = MarkdownWriter(str(data_file), str(output_file))
        assert writer.generate_markdown() is True

        content = output_file.read_text()
        assert "Paper \\| One" in content
        assert "No paper-level citation changes recorded today." in content

    def test_generate_data_readme_includes_zero_change_days(self, tmp_path):
        data_file = tmp_path / "citation_history.json"
        output_file = tmp_path / "citations.md"
        daily_changes_file = tmp_path / "daily_changes.json"

        history = [
            {
                "date": "2024-01-01",
                "total_citations": 10,
                "h_index": 2,
                "i10_index": 1,
                "papers": [{"title": "Paper 1", "citations": 10, "year": "2024"}],
            },
            {
                "date": "2024-01-02",
                "total_citations": 10,
                "h_index": 2,
                "i10_index": 1,
                "papers": [{"title": "Paper 1", "citations": 10, "year": "2024"}],
            },
        ]
        changes = [
            {
                "date": "2024-01-02",
                "total_citations_increase": 0,
                "papers_with_changes": [],
            }
        ]

        data_file.write_text(json.dumps(history))
        daily_changes_file.write_text(json.dumps(changes))

        writer = MarkdownWriter(str(data_file), str(output_file))
        assert writer.generate_data_readme() is True

        readme_content = (tmp_path / "README.md").read_text()
        assert "| Recent Citation Growth | +0 |" in readme_content
        assert "- Papers with new citations: none" in readme_content
