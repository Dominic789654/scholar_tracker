"""Chart generator for citation trend visualization."""

import json
import logging
from logging.handlers import RotatingFileHandler
import plotly.graph_objects as go
import plotly.subplots as sp
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import os
import hashlib


class ChartGenerator:
    """Generate visualization charts for citation trends."""

    def __init__(self, data_file: str, output_dir: str):
        self.data_file = data_file
        self.output_dir = output_dir
        self.cache_file = os.path.join(output_dir, ".chart_cache.json")

    def load_data(self) -> List[Dict[str, Any]]:
        """Load citation history data."""
        with open(self.data_file, 'r') as f:
            history = json.load(f)
        return history

    def _get_data_hash(self, history: List[Dict[str, Any]]) -> str:
        """Generate hash of data for cache validation."""
        # Use last 5 entries for hash (most recent changes matter most)
        recent_data = history[-5:] if len(history) > 5 else history
        data_str = json.dumps(recent_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_cache(self, cache: Dict[str, Any]) -> None:
        """Save cache to file."""
        with open(self.cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def _needs_regeneration(self, history: List[Dict[str, Any]], chart_type: str) -> bool:
        """Check if chart needs regeneration based on data changes."""
        if not os.path.exists(self.cache_file):
            return True

        cache = self._load_cache()
        current_hash = self._get_data_hash(history)
        cached_hash = cache.get(f"{chart_type}_hash")

        # Also check if output files exist
        png_file = os.path.exists(f"{self.output_dir}/{chart_type}.png")
        html_file = os.path.exists(f"{self.output_dir}/{chart_type}.html")

        if not png_file or not html_file:
            return True

        return cached_hash != current_hash

    def generate_charts(self, force: bool = False) -> None:
        """Generate all charts."""
        history = self.load_data()

        # Check if regeneration is needed
        if not force and not self._needs_regeneration(history, "citation_trends"):
            logging.info("Citation trends chart up-to-date, skipping regeneration")
        else:
            logging.info("Generating citation trends chart")
            self._generate_citation_trends(history)
            # Update cache
            cache = self._load_cache()
            cache["citation_trends_hash"] = self._get_data_hash(history)
            cache["citation_trends_date"] = datetime.now().isoformat()
            self._save_cache(cache)

        # Generate individual paper trends
        if not force and not self._needs_regeneration(history, "paper_trends"):
            logging.info("Paper trends chart up-to-date, skipping regeneration")
        else:
            logging.info("Generating paper trends chart")
            self.generate_paper_trends(history)
            # Update cache
            cache = self._load_cache()
            cache["paper_trends_hash"] = self._get_data_hash(history)
            cache["paper_trends_date"] = datetime.now().isoformat()
            self._save_cache(cache)

    def _generate_citation_trends(self, history: List[Dict[str, Any]]) -> None:
        """Generate citation trends chart."""
        # Convert to pandas DataFrame for easier handling
        df = pd.DataFrame([
            {
                'date': datetime.strptime(entry['date'], '%Y-%m-%d'),
                'total_citations': entry['total_citations'],
                'h_index': entry['h_index'],
                'i10_index': entry.get('i10_index', 0)
            } for entry in history
        ])

        # Sort by date
        df = df.sort_values('date')

        # Create figure with secondary y-axis
        fig = sp.make_subplots(specs=[[{"secondary_y": True}]])

        # Add i10-index line (on secondary y-axis with h-index)
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['i10_index'],
                name="i10-index",
                line=dict(color='green', width=2, dash='dot')
            ),
            secondary_y=True
        )

        # Add total citations line
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['total_citations'],
                name="Total Citations",
                line=dict(color='blue', width=2)
            ),
            secondary_y=False
        )

        # Add h-index line
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['h_index'],
                name="H-index",
                line=dict(color='red', width=2)
            ),
            secondary_y=True
        )

        # Update layout
        fig.update_layout(
            title="Citation Metrics Over Time",
            xaxis_title="Date",
            yaxis_title="Total Citations",
            yaxis2_title="H-index / i10-index",
            hovermode='x unified',
            template='plotly_white'
        )

        # Save as HTML (interactive) - use CDN to reduce file size from 3.5MB to ~50KB
        fig.write_html(
            f"{self.output_dir}/citation_trends.html",
            include_plotlyjs='cdn'
        )

        # Save as PNG (static)
        fig.write_image(f"{self.output_dir}/citation_trends.png")

    def generate_paper_trends(self, history: List[Dict[str, Any]]) -> None:
        """Generate trends for individual papers - only top 10 by citation count."""
        # Create DataFrame for paper citations
        paper_data = []
        for entry in history:
            date = datetime.strptime(entry['date'], '%Y-%m-%d')
            for paper in entry['papers']:
                paper_data.append({
                    'date': date,
                    'title': paper['title'],
                    'citations': paper['citations']
                })

        df = pd.DataFrame(paper_data)

        # Get top 10 papers by current citation count
        latest_citations = df.groupby('title')['citations'].last().sort_values(ascending=False)
        top_papers = latest_citations.head(10).index.tolist()

        # Filter to only top 10 papers
        df = df[df['title'].isin(top_papers)]

        # Create figure
        fig = go.Figure()

        # Add line for each paper (only top 10)
        for title in top_papers:
            paper_df = df[df['title'] == title].sort_values('date')
            fig.add_trace(
                go.Scatter(
                    x=paper_df['date'],
                    y=paper_df['citations'],
                    name=title,
                    mode='lines+markers'
                )
            )

        # Update layout
        fig.update_layout(
            title=f"Top 10 Papers by Citation Count",
            xaxis_title="Date",
            yaxis_title="Citations",
            hovermode='x unified',
            template='plotly_white',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02,
                bgcolor='rgba(255,255,255,0.8)'
            ),
            margin=dict(r=150)
        )

        # Save charts - use CDN to reduce file size
        fig.write_html(
            f"{self.output_dir}/paper_trends.html",
            include_plotlyjs='cdn'
        )
        fig.write_image(f"{self.output_dir}/paper_trends.png")
