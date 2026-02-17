# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an academic citation tracker that monitors Google Scholar citations for research papers. It fetches citations daily using the `scholarly` library (with manual HTML parsing fallback), tracks trends over time, and generates visualization charts and markdown summaries.

## Running the Project

### Manually
```bash
python run.py
```
Outputs a colored summary and full report to console automatically.

### Via Shell Script
```bash
./run_daily_update.sh
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Entry Point
- `run.py` - Orchestrates the entire tracking workflow, outputs colored summary on completion

### Core Components

1. **`src/scholar_tracker.py`** - Main tracker logic
   - Fetches citation data via `scholarly` library (with manual BeautifulSoup fallback)
   - Parses paper titles, citation counts, and years
   - Updates `data/citation_history.json` with historical data
   - Tracks daily changes in `data/daily_changes.json`
   - Uses rotating log handler (1MB max, 3 backups)

2. **`src/chart_generator.py`** - Visualization
   - Uses Plotly to generate citation and paper trend charts
   - HTML files use CDN for plotly.js (~50KB instead of 3.5MB embedded)
   - Paper trends show only top 10 papers by citation count
   - Outputs both PNG images and interactive HTML files

3. **`src/markdown_writer.py`** - Report generation
   - Writes markdown summary to `data/citations.md`
   - Generates `data/README.md` with quick statistics overview
   - Includes tables, daily changes, and summary statistics

### Data Flow
```
Google Scholar → scholar_tracker.py (fetch & parse) → citation_history.json
                                                          ↓
                                        chart_generator.py + markdown_writer.py
                                                          ↓
                                citation_trends.png/html, paper_trends.png/html, citations.md, README.md
```

### Data Files (in ./data/)
- `citation_history.json` - Historical data (date, paper titles, citations, h-index, i10-index)
- `daily_changes.json` - Track papers with new citations each day
- `citations.md` - Full markdown summary
- `README.md` - Quick statistics overview
- `citation_trends.png/html` - Citation, H-index, and i10-index trends over time
- `paper_trends.png/html` - Top 10 papers by citation count
- `tracker.log` - Execution logs (rotating, max 1MB per file)

### Output Format
`run.py` automatically displays:
- A colored summary box with key metrics (total citations, H-index, papers, growth)
- Today's changes highlighted in yellow/green
- The full `data/README.md` content with section headers in purple

### GitHub Actions
`.github/workflows/update_citations.yml` runs daily at 00:00 UTC and on manual trigger, executing `python run.py` and committing changes to `data/`.

## Configuration

- Set author ID in `config.json` (currently: `VtK5lwUAAAAJ`)
- Supports both `author_id` (recommended) and `author_query` (fallback)
- The workflow pushes to `origin/main` branch

## Notes

- Data files in `./data/` are gitignored during development (Python cache, .env) but generated reports are tracked
- HTML exports use CDN (`include_plotlyjs='cdn'`) to keep file sizes small
- Log rotation prevents `tracker.log` from growing indefinitely
- Paper trend chart only shows top 10 papers to avoid clutter
