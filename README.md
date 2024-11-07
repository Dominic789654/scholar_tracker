# Scholar Citation Tracker

A Python-based tool that automatically tracks and records citation statistics from Google Scholar. It generates daily reports of citation counts, h-index, and individual paper statistics in a clean markdown format.

## Features

- 🤖 Automated daily tracking of Google Scholar citations
- 📊 Tracks overall citation count and h-index
- 📝 Individual paper citation statistics
- 📈 Historical citation data tracking
- 📑 Clean markdown report generation
- 🔄 GitHub Actions integration for automatic updates

## Setup

### Prerequisites

- Python 3.x
- Git
- GitHub account (for automated tracking)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scholar-citation-tracker.git
cd scholar-citation-tracker
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Configure your Google Scholar profile:
   - Open `run.py`
   - Update the scholar search query in `ScholarTracker("Your Name Institution")`

### Local Usage

Run the tracker manually:
```bash
python run.py
```

The script will:
1. Fetch your latest Google Scholar statistics
2. Update the citation history
3. Generate an updated markdown report in `data/citations.md`

### Automated Tracking

This project includes GitHub Actions configuration for automatic daily updates:

1. Fork this repository
2. Enable GitHub Actions in your fork
3. Ensure the repository has proper write permissions
4. The tracker will run automatically every day at 00:00 UTC

## Project Structure

```
citation_tracker/
├── data/
│   ├── citations.md          # Generated markdown report
│   └── citation_history.json # Historical citation data
├── src/
│   ├── __init__.py
│   ├── scholar_tracker.py    # Core tracking functionality
│   └── markdown_writer.py    # Markdown report generator
├── .github/
│   └── workflows/
│       └── update_citations.yml  # GitHub Actions configuration
├── requirements.txt
├── run.py                    # Main execution script
└── README.md
```

## Output Format

The generated `citations.md` includes:

- Overall citation statistics
- H-index
- Per-paper citation counts
- Citation history (last 10 days)

Example:
```markdown
# Citation Statistics

Last updated: 2024-11-07

## Overall Statistics
- Total Citations: 201
- H-index: 5

## Paper Citations
| Paper | Citations | Year |
| ----- | --------- | ---- |
| Paper Title 1 | 156 | 2023 |
...
```

## Customization

### Modifying the Report Format

Edit `src/markdown_writer.py` to customize the markdown report format.

### Changing Update Frequency

Modify the cron schedule in `.github/workflows/update_citations.yml`:
```yaml
on:
  schedule:
    - cron: '0 0 * * *'  # Current: Daily at midnight UTC
```

## Troubleshooting

### Common Issues

1. **Rate Limiting**: Google Scholar may rate-limit requests. Consider:
   - Reducing update frequency
   - Adding proxy support
   - Implementing retry logic

2. **Authentication Issues**: If GitHub Actions fails to push:
   - Check repository permissions
   - Verify workflow permissions in repository settings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [scholarly](https://scholarly.readthedocs.io/) for Google Scholar API
- GitHub Actions for automation support

## Contact

If you have any questions or suggestions, please open an issue in the repository.
