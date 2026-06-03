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
      --ink: #2b2118;
      --muted: #75695e;
      --line: rgba(83, 61, 42, 0.16);
      --surface: rgba(255, 252, 246, 0.84);
      --surface-strong: #fffaf1;
      --wash: #f6efe6;
      --field: rgba(83, 61, 42, 0.07);
      --clay: #c96442;
      --clay-deep: #8f3f2e;
      --sage: #64785f;
      --blue: #486f89;
      --gold: #b8873d;
      --plum: #765568;
      --shadow: 0 24px 70px rgba(73, 47, 25, 0.12);
      --tight-shadow: 0 14px 34px rgba(73, 47, 25, 0.10);
      --ring: 0 0 0 1px rgba(201, 100, 66, 0.14);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-width: 320px;
      color: var(--ink);
      background:
        linear-gradient(90deg, rgba(86, 68, 48, 0.050) 1px, transparent 1px),
        linear-gradient(180deg, rgba(86, 68, 48, 0.042) 1px, transparent 1px),
        linear-gradient(128deg, rgba(201, 100, 66, 0.12), transparent 32%),
        linear-gradient(310deg, rgba(100, 120, 95, 0.13), transparent 38%),
        linear-gradient(180deg, #fffaf2 0%, #f5ecdf 55%, #efe3d2 100%),
        var(--wash);
      background-attachment: fixed;
      background-size: 30px 30px, 30px 30px, 100% 100%, 100% 100%, 100% 100%;
      font-family: "Avenir Next", "SF Pro Text", "Segoe UI", sans-serif;
      letter-spacing: 0;
      animation: pageWarmth 16s ease-in-out infinite alternate;
    }}

    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      z-index: -1;
      background:
        repeating-linear-gradient(
          135deg,
          rgba(57, 42, 28, 0.018) 0,
          rgba(57, 42, 28, 0.018) 1px,
          transparent 1px,
          transparent 12px
        ),
        repeating-radial-gradient(
          circle at 0 0,
          rgba(43, 33, 24, 0.025) 0,
          rgba(43, 33, 24, 0.025) 1px,
          transparent 1px,
          transparent 7px
        );
      mix-blend-mode: multiply;
      opacity: 0.54;
      animation: paperBreath 9s ease-in-out infinite;
      pointer-events: none;
    }}

    main {{
      width: min(1480px, calc(100% - 44px));
      margin: 0 auto;
      padding: 30px 0 56px;
      position: relative;
    }}

    ::selection {{
      color: #fffaf1;
      background: var(--clay);
    }}

    .topbar {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
      padding: 18px 0 24px;
      position: relative;
      border-bottom: 1px solid var(--line);
      animation: riseIn 720ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
    }}

    .topbar::after {{
      content: "";
      position: absolute;
      left: 0;
      bottom: -1px;
      width: min(360px, 46vw);
      height: 2px;
      background: linear-gradient(90deg, var(--clay), rgba(201, 100, 66, 0));
      transform-origin: left;
      animation: lineDraw 1.1s cubic-bezier(0.2, 0.8, 0.2, 1) 240ms both;
    }}

    .eyebrow {{
      margin: 0 0 8px;
      color: var(--clay-deep);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.10em;
    }}

    h1 {{
      margin: 0;
      max-width: 820px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(38px, 5vw, 64px);
      line-height: 1.05;
      font-weight: 700;
      letter-spacing: 0;
    }}

    .updated {{
      color: var(--muted);
      font-size: 14px;
      text-align: right;
      animation: riseIn 760ms cubic-bezier(0.2, 0.8, 0.2, 1) 90ms both;
    }}

    .updated strong {{
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      font-size: 20px;
    }}

    .runtime-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
      padding: 6px 10px;
      color: var(--clay-deep);
      background: rgba(201, 100, 66, 0.095);
      border: 1px solid rgba(201, 100, 66, 0.18);
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.58);
    }}

    .runtime-pill::before {{
      content: "";
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--clay);
      box-shadow: 0 0 0 5px rgba(201, 100, 66, 0.12);
      animation: pulseDot 1.9s ease-in-out infinite;
    }}

    .summary-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin: 20px 0;
    }}

    .metric {{
      min-height: 112px;
      padding: 16px;
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 248, 238, 0.66)),
        var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--tight-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.76);
      animation: riseIn 760ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
      animation-delay: var(--delay, 0ms);
      transition: transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease;
    }}

    .metric::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.70) 42%, transparent 58%);
      opacity: 0;
      transform: translateX(-120%);
      animation: paperSweep 5.8s ease-in-out infinite;
      animation-delay: calc(var(--delay, 0ms) + 780ms);
      pointer-events: none;
    }}

    .metric::after {{
      content: "";
      position: absolute;
      inset: auto 16px 12px 16px;
      height: 2px;
      background: linear-gradient(90deg, transparent, var(--clay), var(--sage), transparent);
      opacity: 0.55;
      transform: translateX(-42%);
      animation: dataSweep 3.8s ease-in-out infinite;
      animation-delay: var(--delay, 0ms);
    }}

    .metric:hover {{
      transform: translateY(-3px) rotate(-0.25deg);
      border-color: rgba(201, 100, 66, 0.34);
      box-shadow: var(--shadow), var(--ring);
    }}

    .metric strong {{
      display: block;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .metric span {{
      display: block;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 32px;
      line-height: 1;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
    }}

    .metric small {{
      display: block;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }}

    .metric.primary {{
      color: #fffaf1;
      background:
        linear-gradient(135deg, rgba(201, 100, 66, 0.36) 0%, rgba(100, 120, 95, 0.18) 54%, rgba(184, 135, 61, 0.22) 100%),
        #2d231b;
      border-color: transparent;
      box-shadow: var(--shadow), 0 0 0 1px rgba(255, 250, 241, 0.10) inset;
    }}

    .metric.primary strong,
    .metric.primary small {{
      color: rgba(255, 250, 241, 0.74);
    }}

    .control-row {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin: 24px 0 14px;
      animation: riseIn 760ms cubic-bezier(0.2, 0.8, 0.2, 1) 180ms both;
    }}

    .segments {{
      display: inline-flex;
      gap: 4px;
      padding: 4px;
      background: rgba(255, 252, 246, 0.66);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.68);
      backdrop-filter: blur(14px);
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
      transition: color 160ms ease, background 160ms ease, transform 160ms ease;
    }}

    button:hover {{
      color: var(--ink);
      transform: translateY(-1px);
      background: rgba(83, 61, 42, 0.055);
    }}

    button.active {{
      color: #fffaf1;
      background: linear-gradient(135deg, var(--clay), var(--clay-deep));
      box-shadow: 0 9px 22px rgba(143, 63, 46, 0.20);
    }}

    .search {{
      width: min(360px, 100%);
      min-height: 40px;
      padding: 0 14px;
      color: var(--ink);
      background: rgba(255, 252, 246, 0.78);
      border: 1px solid var(--line);
      border-radius: 8px;
      font: inherit;
      outline: none;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.68);
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }}

    .search:focus {{
      border-color: rgba(201, 100, 66, 0.48);
      box-shadow: 0 0 0 3px rgba(201, 100, 66, 0.12);
      transform: translateY(-1px);
    }}

    .dashboard-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.6fr);
      gap: 14px;
    }}

    .panel {{
      min-width: 0;
      padding: 18px;
      position: relative;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 248, 238, 0.68)),
        var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--tight-shadow), inset 0 1px 0 rgba(255, 255, 255, 0.74);
      animation: riseIn 820ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
      animation-delay: var(--delay, 0ms);
      transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }}

    .panel::before {{
      content: "";
      position: absolute;
      inset: 0;
      border-top: 2px solid rgba(201, 100, 66, 0.20);
      pointer-events: none;
    }}

    .panel::after {{
      content: "";
      position: absolute;
      top: 0;
      bottom: 0;
      left: -45%;
      width: 34%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.46), transparent);
      transform: skewX(-10deg) translateX(-120%);
      animation: panelSweep 7.2s ease-in-out infinite;
      animation-delay: calc(var(--delay, 0ms) + 1200ms);
      pointer-events: none;
    }}

    .panel:hover {{
      transform: translateY(-2px);
      border-color: rgba(201, 100, 66, 0.28);
      box-shadow: var(--shadow), var(--ring);
    }}

    .panel h2 {{
      margin: 0 0 12px;
      font-size: 15px;
      line-height: 1.2;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--clay-deep);
    }}

    .plot {{
      width: 100%;
      height: 390px;
      position: relative;
      animation: fadeScale 880ms ease both;
      animation-delay: var(--delay, 0ms);
      transition: opacity 260ms ease, transform 260ms ease;
    }}

    .plot.plot-refreshing {{
      opacity: 0.48;
      transform: translateY(4px) scale(0.992);
    }}

    .plot.plot-ready {{
      opacity: 1;
      transform: translateY(0) scale(1);
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
      scrollbar-width: thin;
      scrollbar-color: rgba(201, 100, 66, 0.42) rgba(83, 61, 42, 0.06);
    }}

    .paper-list::-webkit-scrollbar {{
      width: 8px;
    }}

    .paper-list::-webkit-scrollbar-thumb {{
      background: rgba(201, 100, 66, 0.34);
      border-radius: 999px;
    }}

    .paper-row {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 11px 0;
      border-bottom: 1px solid var(--line);
      animation: slideIn 520ms ease both;
      animation-delay: var(--delay, 0ms);
      transition: padding-left 170ms ease, border-color 170ms ease, background 170ms ease;
    }}

    .paper-row:hover {{
      padding-left: 8px;
      border-color: rgba(201, 100, 66, 0.32);
      background: linear-gradient(90deg, rgba(201, 100, 66, 0.055), transparent);
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
      color: var(--clay-deep);
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
      background: rgba(255, 250, 241, 0.56);
      border: 1px solid var(--line);
      border-radius: 8px;
      animation: slideIn 520ms ease both;
      animation-delay: var(--delay, 0ms);
      transition: transform 170ms ease, border-color 170ms ease, background 170ms ease;
    }}

    .change-day:hover {{
      transform: translateX(4px);
      border-color: rgba(100, 120, 95, 0.30);
      background: rgba(255, 252, 246, 0.78);
    }}

    .change-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      font-weight: 700;
    }}

    .change-head span:last-child {{
      color: var(--sage);
    }}

    .change-paper {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 5px 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      animation: fadeScale 420ms ease both;
      animation-delay: var(--delay, 0ms);
    }}

    .change-paper strong {{
      color: var(--clay-deep);
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
      background: rgba(255, 250, 241, 0.58);
      border: 1px dashed var(--line);
      border-radius: 8px;
      font-size: 13px;
      animation: fadeScale 420ms ease both;
    }}

    @keyframes riseIn {{
      from {{
        opacity: 0;
        transform: translateY(18px) scale(0.992);
      }}
      to {{
        opacity: 1;
        transform: translateY(0) scale(1);
      }}
    }}

    @keyframes slideIn {{
      from {{
        opacity: 0;
        transform: translateX(-14px);
      }}
      to {{
        opacity: 1;
        transform: translateX(0);
      }}
    }}

    @keyframes fadeScale {{
      from {{
        opacity: 0;
        transform: scale(0.985);
      }}
      to {{
        opacity: 1;
        transform: scale(1);
      }}
    }}

    @keyframes dataSweep {{
      0%, 100% {{
        transform: translateX(-56%) scaleX(0.58);
        opacity: 0.18;
      }}
      50% {{
        transform: translateX(56%) scaleX(1);
        opacity: 0.70;
      }}
    }}

    @keyframes lineDraw {{
      from {{
        transform: scaleX(0);
      }}
      to {{
        transform: scaleX(1);
      }}
    }}

    @keyframes paperSweep {{
      0%, 58%, 100% {{
        opacity: 0;
        transform: translateX(-120%);
      }}
      72% {{
        opacity: 0.62;
      }}
      84% {{
        opacity: 0;
        transform: translateX(120%);
      }}
    }}

    @keyframes panelSweep {{
      0%, 64%, 100% {{
        opacity: 0;
        transform: skewX(-10deg) translateX(-120%);
      }}
      76% {{
        opacity: 0.42;
      }}
      88% {{
        opacity: 0;
        transform: skewX(-10deg) translateX(460%);
      }}
    }}

    @keyframes pageWarmth {{
      from {{
        background-position: 0 0, 0 0, 0 0, 0 0, 0 0;
      }}
      to {{
        background-position: 14px 0, 0 18px, 0 0, 0 0, 0 0;
      }}
    }}

    @keyframes paperBreath {{
      0%, 100% {{
        opacity: 0.44;
      }}
      50% {{
        opacity: 0.62;
      }}
    }}

    @keyframes pulseDot {{
      0%, 100% {{
        transform: scale(0.78);
        opacity: 0.62;
      }}
      50% {{
        transform: scale(1.18);
        opacity: 1;
      }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      *,
      *::before,
      *::after {{
        animation-duration: 1ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 1ms !important;
      }}
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

    <section id="summaryGrid" class="summary-grid" aria-label="Citation summary"></section>
    <div id="controlRow" class="control-row"></div>

    <section class="dashboard-grid">
      <div class="stack">
        <article class="panel" style="--delay: 220ms">
          <h2>Citation Momentum</h2>
          <div id="citationTrend" class="plot" style="--delay: 300ms"></div>
        </article>
        <div class="two-col">
          <article class="panel" style="--delay: 300ms">
            <h2>Daily Growth</h2>
            <div id="dailyGrowth" class="plot compact" style="--delay: 380ms"></div>
          </article>
          <article class="panel" style="--delay: 380ms">
            <h2>Top Paper Trajectories</h2>
            <div id="paperTrajectories" class="plot compact" style="--delay: 460ms"></div>
          </article>
        </div>
      </div>

      <aside class="stack">
        <article class="panel" style="--delay: 260ms">
          <h2>Top Papers</h2>
          <div id="paperList" class="paper-list"></div>
        </article>
        <article class="panel" style="--delay: 420ms">
          <h2>Recent Changes</h2>
          <div id="recentChanges" class="changes"></div>
        </article>
      </aside>
    </section>

    <section class="two-col">
      <article class="panel" style="--delay: 500ms">
        <h2>Paper Ranking</h2>
        <div id="paperRanking" class="plot compact" style="--delay: 560ms"></div>
      </article>
      <article class="panel" style="--delay: 580ms">
        <h2>Active Papers This Month</h2>
        <div id="activePapers" class="plot compact" style="--delay: 640ms"></div>
      </article>
    </section>
  </main>

  <script type="module">
    import {{ bind, wire }} from "https://cdn.jsdelivr.net/npm/hyperhtml/+esm";

    window.DASHBOARD_DATA = {data_json};
    const DASHBOARD_DATA = window.DASHBOARD_DATA;
    const html = bind;
    const view = wire;
    const palette = ["#c96442", "#486f89", "#64785f", "#b8873d", "#765568", "#a85e3d", "#3e625b", "#8f6c3d"];
    const ranges = [
      {{ label: "All", value: "all" }},
      {{ label: "1Y", value: "365" }},
      {{ label: "180D", value: "180" }},
      {{ label: "90D", value: "90" }},
      {{ label: "30D", value: "30" }},
    ];
    let selectedRange = "all";
    let searchQuery = "";

    const layoutBase = {{
      paper_bgcolor: "rgba(255,255,255,0)",
      plot_bgcolor: "rgba(255,255,255,0)",
      font: {{ family: "Avenir Next, SF Pro Text, Segoe UI, sans-serif", color: "#2b2118", size: 12 }},
      margin: {{ l: 48, r: 18, t: 8, b: 42 }},
      hovermode: "x unified",
      xaxis: {{ gridcolor: "rgba(83,61,42,0.10)", zeroline: false, tickfont: {{ color: "#75695e" }} }},
      yaxis: {{ gridcolor: "rgba(83,61,42,0.10)", zeroline: false, tickfont: {{ color: "#75695e" }} }},
      legend: {{ orientation: "h", y: 1.12, x: 0, font: {{ size: 11, color: "#2b2118" }} }}
    }};
    const plotConfig = {{ displayModeBar: false, responsive: true }};

    function formatNumber(value, digits = 0) {{
      return Number(value).toLocaleString(undefined, {{
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }});
    }}

    function signedNumber(value) {{
      const number = Number(value || 0);
      return `${{number >= 0 ? "+" : ""}}${{number.toLocaleString()}}`;
    }}

    function metricCards() {{
      const summary = DASHBOARD_DATA.summary;
      return [
        {{
          label: "Total citations",
          value: formatNumber(summary.total_citations),
          raw: summary.total_citations,
          detail: `${{signedNumber(summary.last_30_growth)}} in the last 30 days`,
          primary: true,
        }},
        {{ label: "H-index", value: summary.h_index, raw: summary.h_index, detail: "Current Scholar index" }},
        {{ label: "i10-index", value: summary.i10_index, raw: summary.i10_index, detail: "Current Scholar index" }},
        {{ label: "Papers", value: summary.total_papers, raw: summary.total_papers, detail: "Tracked publications" }},
        {{
          label: "Samples",
          value: summary.samples,
          raw: summary.samples,
          detail: `${{summary.first_date}} to ${{summary.latest_date}}`,
        }},
        {{
          label: "Daily pace",
          value: formatNumber(summary.citations_per_day, 1),
          raw: summary.citations_per_day,
          digits: 1,
          detail: "Average citation growth",
        }},
      ];
    }}

    function renderSummary() {{
      html(document.getElementById("summaryGrid"))`
        ${{metricCards().map((metric, index) => view(metric)`
          <div class=${{metric.primary ? "metric primary" : "metric"}} style=${{`--delay: ${{index * 70}}ms`}}>
            <strong>${{metric.label}}</strong>
            <span class="metric-value" data-value=${{metric.raw}} data-digits=${{metric.digits || 0}}>${{metric.value}}</span>
            <small>${{metric.detail}}</small>
          </div>
        `)}}
      `;
    }}

    function animateMetricValues() {{
      document.querySelectorAll(".metric-value").forEach((node) => {{
        const target = Number(node.dataset.value || 0);
        const digits = Number(node.dataset.digits || 0);
        const startedAt = performance.now();
        const duration = 820 + Math.min(target, 900) * 0.18;

        function tick(now) {{
          const progress = Math.min((now - startedAt) / duration, 1);
          const eased = 1 - Math.pow(1 - progress, 3);
          node.textContent = formatNumber(target * eased, digits);
          if (progress < 1) {{
            requestAnimationFrame(tick);
          }} else {{
            node.textContent = formatNumber(target, digits);
          }}
        }}

        requestAnimationFrame(tick);
      }});
    }}

    function renderControls() {{
      html(document.getElementById("controlRow"))`
        <div class="segments" role="group" aria-label="Time range">
          ${{ranges.map((range) => view(range)`
            <button
              type="button"
              data-range=${{range.value}}
              class=${{selectedRange === range.value ? "active" : ""}}
              onclick=${{() => setRange(range.value)}}
            >${{range.label}}</button>
          `)}}
        </div>
        <input
          class="search"
          id="paperSearch"
          type="search"
          placeholder="Filter papers"
          value=${{searchQuery}}
          oninput=${{(event) => setSearch(event.target.value)}}
        >
      `;
    }}

    function renderRuntimeStatus() {{
      html(document.querySelector(".updated"))`
        Last updated<br><strong>${{DASHBOARD_DATA.summary.latest_date}}</strong>
        <div class="runtime-pill">hyperHTML animated view</div>
      `;
    }}

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
          line: {{ color: "#c96442", width: 3, shape: "spline" }},
          fill: "tozeroy",
          fillcolor: "rgba(201, 100, 66, 0.13)"
        }},
        {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.h_index),
          type: "scatter",
          mode: "lines",
          name: "H-index",
          yaxis: "y2",
          line: {{ color: "#486f89", width: 2, shape: "hv" }}
        }},
        {{
          x: series.map((item) => item.date),
          y: series.map((item) => item.i10_index),
          type: "scatter",
          mode: "lines",
          name: "i10-index",
          yaxis: "y2",
          line: {{ color: "#b8873d", width: 2, dash: "dot", shape: "hv" }}
        }}
      ];
      Plotly.newPlot("citationTrend", traces, {{
        ...layoutBase,
        transition: {{ duration: 420, easing: "cubic-in-out" }},
        yaxis: {{ ...layoutBase.yaxis, title: "Citations" }},
        yaxis2: {{ title: "Index", overlaying: "y", side: "right", gridcolor: "rgba(0,0,0,0)", tickfont: {{ color: "#75695e" }} }}
      }}, plotConfig);
    }}

    function renderDailyGrowth() {{
      const series = filtered(DASHBOARD_DATA.growth_series);
      Plotly.newPlot("dailyGrowth", [{{
        x: series.map((item) => item.date),
        y: series.map((item) => item.increase),
        type: "bar",
        marker: {{
          color: series.map((item) => item.increase > 0 ? "#c96442" : "rgba(83,61,42,0.18)"),
          line: {{ color: "rgba(255,250,241,0.72)", width: 1 }}
        }},
        name: "Daily increase"
      }}], {{
        ...layoutBase,
        margin: {{ l: 42, r: 16, t: 8, b: 42 }},
        transition: {{ duration: 360, easing: "cubic-in-out" }},
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
          line: {{ color: palette[index % palette.length], width: 2, shape: "spline" }}
        }};
      }});
      Plotly.newPlot("paperTrajectories", traces, {{
        ...layoutBase,
        margin: {{ l: 42, r: 16, t: 8, b: 42 }},
        transition: {{ duration: 360, easing: "cubic-in-out" }},
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
        marker: {{ color: papers.map((_, index) => palette[index % palette.length]), line: {{ color: "rgba(255,250,241,0.72)", width: 1 }} }},
        hovertemplate: "%{{y}}<br>%{{x}} citations<extra></extra>"
      }}], {{
        ...layoutBase,
        margin: {{ l: 190, r: 18, t: 8, b: 36 }},
        transition: {{ duration: 360, easing: "cubic-in-out" }},
        showlegend: false,
        yaxis: {{ ...layoutBase.yaxis, tickfont: {{ size: 10 }} }}
      }}, plotConfig);
    }}

    function renderActivePapers() {{
      const papers = DASHBOARD_DATA.active_papers_30d.slice().reverse();
      if (papers.length === 0) {{
        html(document.getElementById("activePapers"))`
          <div class="empty">No paper-level citation changes recorded in the last 30 days.</div>
        `;
        return;
      }}
      Plotly.newPlot("activePapers", [{{
        x: papers.map((paper) => paper.increase),
        y: papers.map((paper) => paper.title),
        type: "bar",
        orientation: "h",
        marker: {{ color: "#486f89", line: {{ color: "rgba(255,250,241,0.72)", width: 1 }} }},
        hovertemplate: "%{{y}}<br>+%{{x}} citations<extra></extra>"
      }}], {{
        ...layoutBase,
        margin: {{ l: 190, r: 18, t: 8, b: 36 }},
        transition: {{ duration: 360, easing: "cubic-in-out" }},
        showlegend: false,
        yaxis: {{ ...layoutBase.yaxis, tickfont: {{ size: 10 }} }}
      }}, plotConfig);
    }}

    function renderPaperList() {{
      const query = searchQuery.trim().toLowerCase();
      const papers = DASHBOARD_DATA.top_papers.filter((paper) => paper.title.toLowerCase().includes(query));
      const list = document.getElementById("paperList");
      if (papers.length === 0) {{
        html(list)`<div class="empty">No matching papers.</div>`;
        return;
      }}
      html(list)`
        ${{papers.map((paper, index) => view(paper)`
        <div class="paper-row" style=${{`--delay: ${{Math.min(index, 18) * 34}}ms`}}>
          <div>
            <div class="paper-title">${{index + 1}}. ${{paper.title}}</div>
            <div class="paper-meta">${{String(paper.year)}}</div>
          </div>
          <div class="paper-count">${{paper.citations.toLocaleString()}}</div>
        </div>
      `)}}
      `;
    }}

    function renderRecentChanges() {{
      const holder = document.getElementById("recentChanges");
      const changes = DASHBOARD_DATA.recent_changes;
      if (changes.length === 0) {{
        html(holder)`<div class="empty">No daily change records yet.</div>`;
        return;
      }}
      html(holder)`
        ${{changes.map((day, index) => {{
        const papers = (day.papers_with_changes || []).slice(0, 5);
        const increase = day.total_citations_increase || 0;
        return view(day)`
          <div class="change-day" style=${{`--delay: ${{index * 45}}ms`}}>
            <div class="change-head">
              <span>${{day.date}}</span>
              <span>${{increase >= 0 ? "+" : ""}}${{increase}}</span>
            </div>
            ${{papers.length
              ? papers.map((paper, paperIndex) => view(paper)`
                <div class="change-paper" style=${{`--delay: ${{index * 45 + paperIndex * 28 + 70}}ms`}}>
                  <span>${{paper.title}}</span>
                  <strong>+${{paper.increase}}</strong>
                </div>
              `)
              : view(day, "empty")`<div class="change-paper"><span>No paper-level changes</span><strong>0</strong></div>`}}
          </div>
        `;
      }})}}
      `;
    }}

    function setRange(range) {{
      selectedRange = range;
      renderControls();
      renderCharts();
    }}

    function setSearch(value) {{
      searchQuery = value;
      renderControls();
      renderPaperList();
      const input = document.getElementById("paperSearch");
      input.focus();
      input.setSelectionRange(searchQuery.length, searchQuery.length);
    }}

    function renderCharts() {{
      if (!window.Plotly) {{
        document.querySelectorAll(".plot").forEach((node) => {{
          html(node)`<div class="empty">Plotly CDN is unavailable. Summary metrics and paper lists are still visible.</div>`;
        }});
        return;
      }}
      document.querySelectorAll(".plot").forEach((node) => {{
        node.classList.remove("plot-ready");
        node.classList.add("plot-refreshing");
      }});
      renderCitationTrend();
      renderDailyGrowth();
      renderPaperTrajectories();
      renderPaperRanking();
      renderActivePapers();
      window.setTimeout(() => {{
        document.querySelectorAll(".plot").forEach((node) => {{
          node.classList.remove("plot-refreshing");
          node.classList.add("plot-ready");
        }});
      }}, 140);
    }}

    function renderAll() {{
      renderRuntimeStatus();
      renderSummary();
      animateMetricValues();
      renderControls();
      renderCharts();
      renderPaperList();
      renderRecentChanges();
    }}

    renderAll();
  </script>
</body>
</html>
"""
