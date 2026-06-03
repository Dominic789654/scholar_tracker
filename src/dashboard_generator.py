"""Generate a static HTML dashboard for citation history."""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from html import escape
from typing import Any, Dict, List, Optional


class DashboardGenerator:
    """Generate a self-contained citation dashboard HTML page."""

    def __init__(
        self,
        history_file: str,
        output_file: str,
        changes_file: Optional[str] = None,
    ):
        self.history_file = history_file
        self.output_file = output_file
        self.changes_file = changes_file or os.path.join(
            os.path.dirname(history_file), "daily_changes.json"
        )

    @staticmethod
    def _load_json_file(path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        with open(path, "r") as file:
            return json.load(file)

    @staticmethod
    def _normalize_title(title: Any) -> str:
        return " ".join(str(title or "").lower().split())

    @staticmethod
    def _parse_date(value: str) -> datetime:
        return datetime.strptime(value, "%Y-%m-%d")

    @staticmethod
    def _clean_index_value(value: Any, previous_value: Optional[int]) -> Optional[int]:
        """Hide likely parsing gaps in index trend lines."""
        if value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if parsed == 0 and previous_value:
            return None
        return parsed

    def _unique_history_by_date(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep the last record for each date, then sort chronologically."""
        by_date: Dict[str, Dict[str, Any]] = {}
        for entry in history:
            date = entry.get("date")
            if date:
                by_date[date] = entry
        return [by_date[date] for date in sorted(by_date)]

    def _unique_changes_by_date(self, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_date: Dict[str, Dict[str, Any]] = {}
        for entry in changes:
            date = entry.get("date")
            if date:
                by_date[date] = entry
        return [by_date[date] for date in sorted(by_date)]

    def _build_payload(self) -> Dict[str, Any]:
        history = self._unique_history_by_date(self._load_json_file(self.history_file, []))
        changes = self._unique_changes_by_date(self._load_json_file(self.changes_file, []))

        if not history:
            raise ValueError("No citation history available for dashboard generation.")

        latest = history[-1]
        first = history[0]
        latest_date = latest["date"]
        latest_dt = self._parse_date(latest_date)
        previous = history[-2] if len(history) > 1 else None

        citation_series = []
        previous_h_index = None
        previous_i10_index = None
        for entry in history:
            h_index = self._clean_index_value(entry.get("h_index"), previous_h_index)
            i10_index = self._clean_index_value(entry.get("i10_index"), previous_i10_index)
            if h_index is not None:
                previous_h_index = h_index
            if i10_index is not None and i10_index > 0:
                previous_i10_index = i10_index
            citation_series.append(
                {
                    "date": entry["date"],
                    "total_citations": entry.get("total_citations", 0),
                    "h_index": h_index,
                    "i10_index": i10_index,
                }
            )

        change_by_date = {
            entry["date"]: entry.get("total_citations_increase", 0) for entry in changes
        }
        growth_series = []
        last_total = None
        for entry in history:
            total = entry.get("total_citations", 0)
            fallback_delta = 0 if last_total is None else total - last_total
            growth_series.append(
                {
                    "date": entry["date"],
                    "increase": change_by_date.get(entry["date"], fallback_delta),
                }
            )
            last_total = total

        latest_papers = latest.get("papers", [])
        top_papers = sorted(
            latest_papers,
            key=lambda paper: paper.get("citations", 0),
            reverse=True,
        )
        top_papers_payload = [
            {
                "title": paper.get("title", "Untitled"),
                "citations": paper.get("citations", 0),
                "year": paper.get("year", "N/A"),
            }
            for paper in top_papers[:15]
        ]

        top_trend_papers = top_papers[:8]
        top_trend_keys = [self._normalize_title(paper.get("title")) for paper in top_trend_papers]
        canonical_titles = {
            self._normalize_title(paper.get("title")): paper.get("title", "Untitled")
            for paper in top_trend_papers
        }
        paper_trends = {
            canonical_titles[key]: [] for key in top_trend_keys if key in canonical_titles
        }

        for entry in history:
            paper_lookup = {
                self._normalize_title(paper.get("title")): paper.get("citations", 0)
                for paper in entry.get("papers", [])
            }
            for key in top_trend_keys:
                title = canonical_titles.get(key)
                if title:
                    paper_trends[title].append(
                        {
                            "date": entry["date"],
                            "citations": paper_lookup.get(key),
                        }
                    )

        recent_changes = list(reversed(changes[-10:]))
        active_papers_30d: Dict[str, int] = defaultdict(int)
        cutoff_30d = latest_dt - timedelta(days=30)
        for entry in changes:
            try:
                entry_date = self._parse_date(entry["date"])
            except (KeyError, ValueError):
                continue
            if entry_date < cutoff_30d:
                continue
            for paper in entry.get("papers_with_changes", []):
                active_papers_30d[paper.get("title", "Untitled")] += paper.get("increase", 0)

        active_papers_payload = [
            {"title": title, "increase": increase}
            for title, increase in sorted(
                active_papers_30d.items(), key=lambda item: item[1], reverse=True
            )[:10]
            if increase > 0
        ]

        last_30_growth = sum(
            item["increase"]
            for item in growth_series
            if self._parse_date(item["date"]) >= cutoff_30d
        )
        latest_growth = (
            latest.get("total_citations", 0) - previous.get("total_citations", 0)
            if previous
            else 0
        )
        first_date = self._parse_date(first["date"])
        days_elapsed = max((latest_dt - first_date).days, 1)

        summary = {
            "latest_date": latest_date,
            "first_date": first["date"],
            "samples": len(history),
            "total_citations": latest.get("total_citations", 0),
            "h_index": latest.get("h_index", 0),
            "i10_index": latest.get("i10_index", 0),
            "total_papers": len(latest_papers),
            "latest_growth": latest_growth,
            "last_30_growth": last_30_growth,
            "all_time_growth": latest.get("total_citations", 0)
            - first.get("total_citations", 0),
            "citations_per_day": (
                latest.get("total_citations", 0) - first.get("total_citations", 0)
            )
            / days_elapsed,
            "active_papers_30d": len(active_papers_payload),
        }

        return {
            "summary": summary,
            "citation_series": citation_series,
            "growth_series": growth_series,
            "top_papers": top_papers_payload,
            "paper_trends": paper_trends,
            "recent_changes": recent_changes,
            "active_papers_30d": active_papers_payload,
        }

    def generate_dashboard(self) -> bool:
        """Generate the dashboard HTML file."""
        payload = self._build_payload()
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        with open(self.output_file, "w") as file:
            file.write(self._render_html(payload))
        return True

    def _render_html(self, payload: Dict[str, Any]) -> str:
        summary = payload["summary"]
        data_json = json.dumps(payload, ensure_ascii=True)
        latest_date = escape(summary["latest_date"])
        total_citations = f"{summary['total_citations']:,}"
        h_index = summary["h_index"]
        i10_index = summary["i10_index"]
        total_papers = summary["total_papers"]
        last_30_growth = f"{summary['last_30_growth']:+,}"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Citation Dashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --ink: #17201d;
      --muted: #66736e;
      --line: #d8ded8;
      --surface: #ffffff;
      --wash: #f4f7f4;
      --field: #e8eee9;
      --green: #237b4b;
      --blue: #285f91;
      --gold: #ba7a1d;
      --red: #b54a3d;
      --shadow: 0 20px 60px rgba(26, 42, 34, 0.10);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-width: 320px;
      color: var(--ink);
      background:
        linear-gradient(90deg, rgba(23, 32, 29, 0.035) 1px, transparent 1px),
        linear-gradient(180deg, rgba(23, 32, 29, 0.035) 1px, transparent 1px),
        var(--wash);
      background-size: 28px 28px;
      font-family: "Avenir Next", "Helvetica Neue", "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}

    main {{
      width: min(1480px, calc(100% - 40px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}

    .topbar {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
      padding: 18px 0 22px;
      border-bottom: 1px solid var(--line);
    }}

    .eyebrow {{
      margin: 0 0 8px;
      color: var(--green);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
    }}

    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 42px;
      line-height: 1.05;
      font-weight: 700;
    }}

    .updated {{
      color: var(--muted);
      font-size: 14px;
      text-align: right;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}

    .metric {{
      min-height: 112px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
    }}

    .metric strong {{
      display: block;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .metric span {{
      display: block;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 32px;
      line-height: 1;
      font-weight: 700;
    }}

    .metric small {{
      display: block;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }}

    .metric.primary {{
      color: white;
      background: linear-gradient(135deg, #17201d 0%, #285f47 100%);
      border-color: transparent;
      box-shadow: var(--shadow);
    }}

    .metric.primary strong,
    .metric.primary small {{
      color: rgba(255, 255, 255, 0.72);
    }}

    .control-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin: 22px 0 12px;
    }}

    .segments {{
      display: inline-flex;
      gap: 4px;
      padding: 4px;
      background: var(--field);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}

    button {{
      min-height: 34px;
      padding: 0 14px;
      color: var(--muted);
      background: transparent;
      border: 0;
      border-radius: 6px;
      font: inherit;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
    }}

    button.active {{
      color: white;
      background: var(--ink);
    }}

    .search {{
      width: min(360px, 100%);
      min-height: 40px;
      padding: 0 14px;
      color: var(--ink);
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      font: inherit;
    }}

    .dashboard-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.6fr);
      gap: 14px;
    }}

    .panel {{
      min-width: 0;
      padding: 18px;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 12px 30px rgba(26, 42, 34, 0.06);
    }}

    .panel h2 {{
      margin: 0 0 12px;
      font-size: 15px;
      line-height: 1.2;
      text-transform: uppercase;
    }}

    .plot {{
      width: 100%;
      height: 390px;
    }}

    .plot.compact {{
      height: 315px;
    }}

    .stack {{
      display: grid;
      gap: 14px;
    }}

    .paper-list {{
      display: grid;
      gap: 8px;
      max-height: 530px;
      overflow: auto;
      padding-right: 4px;
    }}

    .paper-row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
    }}

    .paper-title {{
      min-width: 0;
      font-size: 13px;
      line-height: 1.35;
      font-weight: 650;
    }}

    .paper-meta {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }}

    .paper-count {{
      color: var(--blue);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 22px;
      font-weight: 700;
      white-space: nowrap;
    }}

    .changes {{
      display: grid;
      gap: 10px;
    }}

    .change-day {{
      padding: 12px;
      background: #fbfcfb;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}

    .change-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      font-weight: 700;
    }}

    .change-head span:last-child {{
      color: var(--green);
    }}

    .change-paper {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 5px 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}

    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 14px;
    }}

    .empty {{
      padding: 18px;
      color: var(--muted);
      background: #fbfcfb;
      border: 1px dashed var(--line);
      border-radius: 8px;
      font-size: 13px;
    }}

    @media (max-width: 1100px) {{
      .summary-grid {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}

      .dashboard-grid,
      .two-col {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 680px) {{
      main {{
        width: min(100% - 24px, 1480px);
        padding-top: 18px;
      }}

      .topbar {{
        grid-template-columns: 1fr;
        align-items: start;
      }}

      h1 {{
        font-size: 32px;
      }}

      .updated {{
        text-align: left;
      }}

      .summary-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .metric {{
        min-height: 104px;
      }}

      .metric span {{
        font-size: 26px;
      }}

      .plot {{
        height: 320px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="topbar">
      <div>
        <p class="eyebrow">Google Scholar Citation Tracker</p>
        <h1>Citation Dashboard</h1>
      </div>
      <div class="updated">Last updated<br><strong>{latest_date}</strong></div>
    </header>

    <section class="summary-grid" aria-label="Citation summary">
      <div class="metric primary">
        <strong>Total citations</strong>
        <span>{total_citations}</span>
        <small>{last_30_growth} in the last 30 days</small>
      </div>
      <div class="metric">
        <strong>H-index</strong>
        <span>{h_index}</span>
        <small>Current Scholar index</small>
      </div>
      <div class="metric">
        <strong>i10-index</strong>
        <span>{i10_index}</span>
        <small>Current Scholar index</small>
      </div>
      <div class="metric">
        <strong>Papers</strong>
        <span>{total_papers}</span>
        <small>Tracked publications</small>
      </div>
      <div class="metric">
        <strong>Samples</strong>
        <span>{summary['samples']}</span>
        <small>{escape(summary['first_date'])} to {latest_date}</small>
      </div>
      <div class="metric">
        <strong>Daily pace</strong>
        <span>{summary['citations_per_day']:.1f}</span>
        <small>Average citation growth</small>
      </div>
    </section>

    <div class="control-row">
      <div class="segments" role="group" aria-label="Time range">
        <button type="button" data-range="all" class="active">All</button>
        <button type="button" data-range="365">1Y</button>
        <button type="button" data-range="180">180D</button>
        <button type="button" data-range="90">90D</button>
        <button type="button" data-range="30">30D</button>
      </div>
      <input class="search" id="paperSearch" type="search" placeholder="Filter papers">
    </div>

    <section class="dashboard-grid">
      <div class="stack">
        <article class="panel">
          <h2>Citation Momentum</h2>
          <div id="citationTrend" class="plot"></div>
        </article>
        <div class="two-col">
          <article class="panel">
            <h2>Daily Growth</h2>
            <div id="dailyGrowth" class="plot compact"></div>
          </article>
          <article class="panel">
            <h2>Top Paper Trajectories</h2>
            <div id="paperTrajectories" class="plot compact"></div>
          </article>
        </div>
      </div>

      <aside class="stack">
        <article class="panel">
          <h2>Top Papers</h2>
          <div id="paperList" class="paper-list"></div>
        </article>
        <article class="panel">
          <h2>Recent Changes</h2>
          <div id="recentChanges" class="changes"></div>
        </article>
      </aside>
    </section>

    <section class="two-col">
      <article class="panel">
        <h2>Paper Ranking</h2>
        <div id="paperRanking" class="plot compact"></div>
      </article>
      <article class="panel">
        <h2>Active Papers This Month</h2>
        <div id="activePapers" class="plot compact"></div>
      </article>
    </section>
  </main>

  <script>
    window.DASHBOARD_DATA = {data_json};
    const DASHBOARD_DATA = window.DASHBOARD_DATA;
    const palette = ["#237b4b", "#285f91", "#ba7a1d", "#b54a3d", "#5956a5", "#10827a", "#8a5a24", "#5f6f2a"];
    let selectedRange = "all";

    const layoutBase = {{
      paper_bgcolor: "rgba(255,255,255,0)",
      plot_bgcolor: "rgba(255,255,255,0)",
      font: {{ family: "Avenir Next, Helvetica Neue, Segoe UI, sans-serif", color: "#17201d", size: 12 }},
      margin: {{ l: 48, r: 18, t: 8, b: 42 }},
      hovermode: "x unified",
      xaxis: {{ gridcolor: "#e6ebe6", zeroline: false }},
      yaxis: {{ gridcolor: "#e6ebe6", zeroline: false }},
      legend: {{ orientation: "h", y: 1.12, x: 0, font: {{ size: 11 }} }}
    }};
    const plotConfig = {{ displayModeBar: false, responsive: true }};

    function parseDate(item) {{
      return new Date(item.date + "T00:00:00");
    }}

    function filtered(series) {{
      if (selectedRange === "all" || series.length === 0) return series;
      const last = parseDate(series[series.length - 1]);
      const cutoff = new Date(last);
      cutoff.setDate(cutoff.getDate() - Number(selectedRange));
      return series.filter((item) => parseDate(item) >= cutoff);
    }}

    function renderCitationTrend() {{
      const series = filtered(DASHBOARD_DATA.citation_series);
      const traces = [
        {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.total_citations),
          type: "scatter",
          mode: "lines",
          name: "Citations",
          line: {{ color: "#237b4b", width: 3 }},
          fill: "tozeroy",
          fillcolor: "rgba(35, 123, 75, 0.12)"
        }},
        {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.h_index),
          type: "scatter",
          mode: "lines",
          name: "H-index",
          yaxis: "y2",
          line: {{ color: "#285f91", width: 2 }}
        }},
        {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.i10_index),
          type: "scatter",
          mode: "lines",
          name: "i10-index",
          yaxis: "y2",
          line: {{ color: "#ba7a1d", width: 2, dash: "dot" }}
        }}
      ];
      Plotly.newPlot("citationTrend", traces, {{
        ...layoutBase,
        yaxis: {{ ...layoutBase.yaxis, title: "Citations" }},
        yaxis2: {{ title: "Index", overlaying: "y", side: "right", gridcolor: "rgba(0,0,0,0)" }}
      }}, plotConfig);
    }}

    function renderDailyGrowth() {{
      const series = filtered(DASHBOARD_DATA.growth_series);
      Plotly.newPlot("dailyGrowth", [{{
        x: series.map((item) => item.date),
        y: series.map((item) => item.increase),
        type: "bar",
        marker: {{
          color: series.map((item) => item.increase > 0 ? "#237b4b" : "#c8d1ca")
        }},
        name: "Daily increase"
      }}], {{
        ...layoutBase,
        margin: {{ l: 42, r: 16, t: 8, b: 42 }},
        hovermode: "closest",
        showlegend: false
      }}, plotConfig);
    }}

    function renderPaperTrajectories() {{
      const traces = Object.entries(DASHBOARD_DATA.paper_trends).map(([title, values], index) => {{
        const series = filtered(values);
        return {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.citations),
          type: "scatter",
          mode: "lines",
          name: title,
          line: {{ color: palette[index % palette.length], width: 2 }}
        }};
      }});
      Plotly.newPlot("paperTrajectories", traces, {{
        ...layoutBase,
        margin: {{ l: 42, r: 16, t: 8, b: 42 }},
        legend: {{ orientation: "h", y: -0.22, x: 0, font: {{ size: 10 }} }}
      }}, plotConfig);
    }}

    function renderPaperRanking() {{
      const papers = DASHBOARD_DATA.top_papers.slice(0, 12).reverse();
      Plotly.newPlot("paperRanking", [{{
        x: papers.map((paper) => paper.citations),
        y: papers.map((paper) => paper.title),
        type: "bar",
        orientation: "h",
        marker: {{ color: papers.map((_, index) => palette[index % palette.length]) }},
        hovertemplate: "%{{y}}<br>%{{x}} citations<extra></extra>"
      }}], {{
        ...layoutBase,
        margin: {{ l: 190, r: 18, t: 8, b: 36 }},
        showlegend: false,
        yaxis: {{ ...layoutBase.yaxis, tickfont: {{ size: 10 }} }}
      }}, plotConfig);
    }}

    function renderActivePapers() {{
      const papers = DASHBOARD_DATA.active_papers_30d.slice().reverse();
      if (papers.length === 0) {{
        document.getElementById("activePapers").innerHTML = '<div class="empty">No paper-level citation changes recorded in the last 30 days.</div>';
        return;
      }}
      Plotly.newPlot("activePapers", [{{
        x: papers.map((paper) => paper.increase),
        y: papers.map((paper) => paper.title),
        type: "bar",
        orientation: "h",
        marker: {{ color: "#285f91" }},
        hovertemplate: "%{{y}}<br>+%{{x}} citations<extra></extra>"
      }}], {{
        ...layoutBase,
        margin: {{ l: 190, r: 18, t: 8, b: 36 }},
        showlegend: false,
        yaxis: {{ ...layoutBase.yaxis, tickfont: {{ size: 10 }} }}
      }}, plotConfig);
    }}

    function renderPaperList() {{
      const query = document.getElementById("paperSearch").value.trim().toLowerCase();
      const papers = DASHBOARD_DATA.top_papers.filter((paper) => paper.title.toLowerCase().includes(query));
      const list = document.getElementById("paperList");
      if (papers.length === 0) {{
        list.innerHTML = '<div class="empty">No matching papers.</div>';
        return;
      }}
      list.innerHTML = papers.map((paper, index) => `
        <div class="paper-row">
          <div>
            <div class="paper-title">${{index + 1}}. ${{escapeHtml(paper.title)}}</div>
            <div class="paper-meta">${{escapeHtml(String(paper.year))}}</div>
          </div>
          <div class="paper-count">${{paper.citations.toLocaleString()}}</div>
        </div>
      `).join("");
    }}

    function renderRecentChanges() {{
      const holder = document.getElementById("recentChanges");
      const changes = DASHBOARD_DATA.recent_changes;
      if (changes.length === 0) {{
        holder.innerHTML = '<div class="empty">No daily change records yet.</div>';
        return;
      }}
      holder.innerHTML = changes.map((day) => {{
        const papers = (day.papers_with_changes || []).slice(0, 5);
        const paperRows = papers.length
          ? papers.map((paper) => `
              <div class="change-paper">
                <span>${{escapeHtml(paper.title)}}</span>
                <strong>+${{paper.increase}}</strong>
              </div>
            `).join("")
          : '<div class="change-paper"><span>No paper-level changes</span><strong>0</strong></div>';
        const increase = day.total_citations_increase || 0;
        return `
          <div class="change-day">
            <div class="change-head">
              <span>${{escapeHtml(day.date)}}</span>
              <span>${{increase >= 0 ? "+" : ""}}${{increase}}</span>
            </div>
            ${{paperRows}}
          </div>
        `;
      }}).join("");
    }}

    function escapeHtml(value) {{
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }}

    function renderAll() {{
      if (!window.Plotly) {{
        document.querySelectorAll(".plot").forEach((node) => {{
          node.innerHTML = '<div class="empty">Plotly CDN is unavailable. Summary metrics and paper lists are still visible.</div>';
        }});
        renderPaperList();
        renderRecentChanges();
        return;
      }}
      renderCitationTrend();
      renderDailyGrowth();
      renderPaperTrajectories();
      renderPaperRanking();
      renderActivePapers();
      renderPaperList();
      renderRecentChanges();
    }}

    document.querySelectorAll("[data-range]").forEach((button) => {{
      button.addEventListener("click", () => {{
        selectedRange = button.dataset.range;
        document.querySelectorAll("[data-range]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        renderAll();
      }});
    }});
    document.getElementById("paperSearch").addEventListener("input", renderPaperList);
    renderAll();
  </script>
</body>
</html>
"""
