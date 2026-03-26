"""Chart generator for citation trend visualization."""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generate visualization charts for citation trends."""

    def __init__(self, data_file: str, output_dir: str):
        self.data_file = data_file
        self.output_dir = output_dir
        self.cache_file = os.path.join(output_dir, ".chart_cache.json")

    def _output_path(self, name: str) -> str:
        return os.path.join(self.output_dir, name)

    def load_data(self) -> List[Dict[str, Any]]:
        """Load citation history data."""
        with open(self.data_file, "r") as f:
            return json.load(f)

    def _get_data_hash(self, history: List[Dict[str, Any]]) -> str:
        """Generate hash of full history for cache validation."""
        data_str = json.dumps(history, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as f:
                return json.load(f)
        return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        """Save cache to file."""
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(cache, f, indent=2)

    def _needs_regeneration(self, history: List[Dict[str, Any]], chart_type: str) -> bool:
        """Check if chart needs regeneration based on data changes."""
        cache = self._load_cache()
        current_hash = self._get_data_hash(history)
        cached_hash = cache.get(f"{chart_type}_hash")

        png_file = os.path.exists(self._output_path(f"{chart_type}.png"))
        html_file = os.path.exists(self._output_path(f"{chart_type}.html"))
        if not png_file or not html_file:
            return True

        return cached_hash != current_hash

    def generate_charts(self, force: bool = False) -> None:
        """Generate all charts."""
        history = self.load_data()
        if not history:
            logger.info("No history data available, skipping chart generation")
            return

        os.makedirs(self.output_dir, exist_ok=True)

        if force or self._needs_regeneration(history, "citation_trends"):
            logger.info("Generating citation trends chart")
            self._generate_citation_trends(history)
            cache = self._load_cache()
            cache["citation_trends_hash"] = self._get_data_hash(history)
            cache["citation_trends_date"] = datetime.now().isoformat()
            self._save_cache(cache)
        else:
            logger.info("Citation trends chart up-to-date, skipping regeneration")

        if force or self._needs_regeneration(history, "paper_trends"):
            logger.info("Generating paper trends chart")
            self.generate_paper_trends(history)
            cache = self._load_cache()
            cache["paper_trends_hash"] = self._get_data_hash(history)
            cache["paper_trends_date"] = datetime.now().isoformat()
            self._save_cache(cache)
        else:
            logger.info("Paper trends chart up-to-date, skipping regeneration")

    def _generate_citation_trends(self, history: List[Dict[str, Any]]) -> None:
        """Generate citation trends chart."""
        df = pd.DataFrame(
            [
                {
                    "date": datetime.strptime(entry["date"], "%Y-%m-%d"),
                    "total_citations": entry["total_citations"],
                    "h_index": entry["h_index"],
                    "i10_index": entry.get("i10_index", 0),
                }
                for entry in history
            ]
        ).sort_values("date")

        fig = sp.make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["i10_index"],
                name="i10-index",
                line=dict(color="green", width=2, dash="dot"),
            ),
            secondary_y=True,
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["total_citations"],
                name="Total Citations",
                line=dict(color="blue", width=2),
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["h_index"],
                name="H-index",
                line=dict(color="red", width=2),
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title="Citation Metrics Over Time",
            xaxis_title="Date",
            yaxis_title="Total Citations",
            yaxis2_title="H-index / i10-index",
            hovermode="x unified",
            template="plotly_white",
        )

        fig.write_html(self._output_path("citation_trends.html"), include_plotlyjs="cdn")
        fig.write_image(self._output_path("citation_trends.png"))

    def generate_paper_trends(self, history: List[Dict[str, Any]]) -> None:
        """Generate trends for individual papers - only top 10 by citation count."""
        paper_data = []
        for entry in history:
            date = datetime.strptime(entry["date"], "%Y-%m-%d")
            for paper in entry["papers"]:
                paper_data.append(
                    {
                        "date": date,
                        "title": paper["title"],
                        "citations": paper["citations"],
                    }
                )

        if not paper_data:
            logger.info("No paper data available, skipping paper trends chart")
            return

        df = pd.DataFrame(paper_data)
        latest_citations = df.groupby("title")["citations"].last().sort_values(ascending=False)
        top_papers = latest_citations.head(10).index.tolist()
        df = df[df["title"].isin(top_papers)]

        fig = go.Figure()
        for title in top_papers:
            paper_df = df[df["title"] == title].sort_values("date")
            fig.add_trace(
                go.Scatter(
                    x=paper_df["date"],
                    y=paper_df["citations"],
                    name=title,
                    mode="lines+markers",
                )
            )

        fig.update_layout(
            title="Top 10 Papers by Citation Count",
            xaxis_title="Date",
            yaxis_title="Citations",
            hovermode="x unified",
            template="plotly_white",
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                bgcolor="rgba(255,255,255,0.8)",
            ),
            margin=dict(r=150),
        )

        fig.write_html(self._output_path("paper_trends.html"), include_plotlyjs="cdn")
        fig.write_image(self._output_path("paper_trends.png"))
