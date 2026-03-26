"""Markdown writer for generating citation reports."""

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MarkdownWriter:
    """Generate markdown reports from citation history."""

    def __init__(self, data_file: str, output_file: str):
        self.data_file = data_file
        self.output_file = output_file
        self.data_dir = os.path.dirname(output_file)
        self.daily_changes_file = os.path.join(self.data_dir, "daily_changes.json")

    @staticmethod
    def _load_json_file(path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        with open(path, "r") as f:
            return json.load(f)

    @staticmethod
    def _escape_markdown_cell(value: Any) -> str:
        text = str(value)
        return text.replace("|", "\\|").replace("\n", " ").strip()

    def _load_history(self) -> List[Dict[str, Any]]:
        return self._load_json_file(self.data_file, default=[])

    def _get_latest_changes(self, latest_date: str) -> Optional[Dict[str, Any]]:
        daily_changes = self._load_json_file(self.daily_changes_file, default=[])
        if not daily_changes:
            return None

        latest_changes = daily_changes[-1]
        if latest_changes.get("date") != latest_date:
            return None
        return latest_changes

    def generate_markdown(self) -> bool:
        """Generate markdown report from citation history."""
        try:
            history = self._load_history()
            if not history:
                return False

            latest = history[-1]
            latest_changes = self._get_latest_changes(latest["date"])
            content = [
                "# Citation Statistics",
                f"\nLast updated: {latest['date']}",
                "\n## Overall Statistics",
                f"- Total Citations: {latest['total_citations']}",
                f"- H-index: {latest['h_index']}",
                f"- i10-index: {latest.get('i10_index', 'N/A')}",
            ]

            if latest_changes:
                content.extend(
                    [
                        "\n## Today's Citation Changes",
                        (
                            f"\nTotal increase: "
                            f"{latest_changes['total_citations_increase']:+d} citations"
                        ),
                    ]
                )
                papers_with_changes = latest_changes.get("papers_with_changes", [])
                if papers_with_changes:
                    content.extend(
                        [
                            "\n| Paper | Previous | New | Increase |",
                            "| ----- | -------- | --- | -------- |",
                        ]
                    )
                    for paper in papers_with_changes:
                        content.append(
                            "| "
                            f"{self._escape_markdown_cell(paper['title'])} | "
                            f"{paper['previous_citations']} | "
                            f"{paper['new_citations']} | "
                            f"{paper['increase']:+d} |"
                        )
                else:
                    content.append("\nNo paper-level citation changes recorded today.")

            sorted_papers = sorted(
                latest["papers"],
                key=lambda item: item["citations"],
                reverse=True,
            )
            content.extend(
                [
                    "\n## Paper Citations",
                    "\n| Paper | Citations | Year |",
                    "| ----- | --------- | ---- |",
                ]
            )
            for paper in sorted_papers:
                content.append(
                    "| "
                    f"{self._escape_markdown_cell(paper['title'])} | "
                    f"{paper['citations']} | "
                    f"{self._escape_markdown_cell(paper['year'])} |"
                )

            content.extend(
                [
                    "\n## Citation History",
                    "\n| Date | Total Citations | H-index |",
                    "| ---- | --------------- | ------- |",
                ]
            )
            for entry in reversed(history[-10:]):
                content.append(
                    f"| {entry['date']} | {entry['total_citations']} | {entry['h_index']} |"
                )

            content.extend(
                [
                    "\n## Citation Trends",
                    "\n### Overall Trends",
                    "![Citation Trends](citation_trends.png)",
                    "\n### Individual Paper Trends",
                    "![Paper Trends](paper_trends.png)",
                    "\n*For interactive charts, see [citation_trends.html](citation_trends.html) and [paper_trends.html](paper_trends.html)*",
                ]
            )

            with open(self.output_file, "w") as f:
                f.write("\n".join(content))
            return True
        except Exception as exc:
            logger.exception("Error generating markdown: %s", exc)
            return False

    def generate_data_readme(self) -> bool:
        """Generate README.md for the data directory."""
        try:
            history = self._load_history()
            if not history:
                return False

            latest = history[-1]
            total_papers = len(latest["papers"])
            citation_growth = 0
            if len(history) > 1:
                prev = history[-2]
                citation_growth = latest["total_citations"] - prev["total_citations"]

            latest_changes = self._get_latest_changes(latest["date"])
            content = [
                "# Citation Statistics Overview",
                "\n## Latest Statistics",
                f"*Last Updated: {latest['date']}*",
                "\n### Quick Summary",
                "| Metric | Value |",
                "| ------ | ----- |",
                f"| Total Citations | {latest['total_citations']} |",
                f"| H-index | {latest['h_index']} |",
                f"| i10-index | {latest.get('i10_index', 'N/A')} |",
                f"| Total Papers | {total_papers} |",
                f"| Recent Citation Growth | {citation_growth:+d} |",
            ]

            if latest_changes:
                content.extend(
                    [
                        "\n### Today's Changes",
                        (
                            f"- Total Citations Increase: "
                            f"{latest_changes['total_citations_increase']:+d}"
                        ),
                    ]
                )
                papers_with_changes = latest_changes.get("papers_with_changes", [])
                if papers_with_changes:
                    content.append("- Papers with new citations:")
                    for paper in papers_with_changes:
                        content.append(
                            f"  - {paper['title']}: {paper['increase']:+d} citations"
                        )
                else:
                    content.append("- Papers with new citations: none")

            readme_path = os.path.join(self.data_dir, "README.md")
            with open(readme_path, "w") as f:
                f.write("\n".join(content))
            return True
        except Exception as exc:
            logger.exception("Error generating data README: %s", exc)
            return False
