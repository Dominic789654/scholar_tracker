# Scholar Citation Tracker

[![Update Citations](https://github.com/xiangliu1223/scholar_tracker/actions/workflows/update_citations.yml/badge.svg)](https://github.com/xiangliu1223/scholar_tracker/actions/workflows/update_citations.yml)

A Python-based tool that automatically tracks and records citation statistics from Google Scholar. It generates daily reports of citation counts, h-index, and individual paper statistics in a clean markdown format.

## Features

- 🤖 Automated daily tracking of Google Scholar citations
- 📊 Tracks overall citation count and h-index
- 📝 Individual paper citation statistics
- 📈 Historical citation data tracking
- 📑 Clean markdown report generation
- ⚙️ Easy configuration with Google Scholar ID
- 🔄 GitHub Actions integration for automatic updates

## Setup

### Prerequisites

- Python 3.x
- Git

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/scholar-citation-tracker.git
    cd scholar-citation-tracker
    ```

2.  **Install required packages:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your Google Scholar Profile:**

    The most reliable way to track your profile is by using your Google Scholar ID.

    **How to find your Google Scholar ID:**
    1.  Go to your Google Scholar profile page.
    2.  Look at the URL in your browser's address bar.
    3.  The URL will look something like this: `https://scholar.google.com/citations?user=VtK5lwUAAAAJ&hl=en`
    4.  Your Scholar ID is the string of characters after `user=`. In the example above, it's `VtK5lwUAAAAJ`.

    **Update the configuration:**
    - Open the `config.json` file.
    - Replace `"YOUR_SCHOLAR_ID_HERE"` with your actual Google Scholar ID:
    ```json
    {
      "author_id": "VtK5lwUAAAAJ",
      "author_query": null
    }
    ```

    Alternatively, you can track by name, but this is less reliable:
    ```json
    {
      "author_id": null,
      "author_query": "Your Name Institution"
    }
    ```

### Local Usage

Run the tracker manually from your terminal:
```bash
python run.py
```

The script will:
1.  Fetch your latest Google Scholar statistics using the configured ID.
2.  Update the citation history in `data/citation_history.json`.
3.  Generate an updated markdown report in `data/citations.md`.
4.  Create trend charts in the `data/` directory.

### Automated Tracking with GitHub Actions

This project can be automated to run daily using GitHub Actions.

1.  **Fork this repository.**
2.  **Enable GitHub Actions in your fork:**
    - Go to your repository's "Settings" > "Actions" > "General".
    - Under "Workflow permissions," select "Read and write permissions."
3.  The tracker will automatically run daily at 00:00 UTC. You can change the schedule in `.github/workflows/update_citations.yml`.

## Project Structure

```
scholar_tracker/
├── .github/
│   └── workflows/
│       └── update_citations.yml  # GitHub Actions configuration
├── data/
│   ├── citation_history.json # Historical citation data
│   ├── citations.md          # Generated markdown report
│   ├── citation_trends.png   # Trend chart for citations
│   ├── paper_trends.png      # Trend chart for top papers
│   └── tracker.log           # Log file for debugging
├── src/
│   ├── scholar_tracker.py    # Core tracking functionality
│   ├── markdown_writer.py    # Markdown report generator
│   └── chart_generator.py    # Chart generation logic
├── config.json               # Configuration file
├── requirements.txt
├── run.py                    # Main execution script
└── README.md
```

## Output Example

The generated `data/citations.md` includes:

- Overall citation statistics (Total Citations, H-index)
- A summary of new citations since the last update.
- Per-paper citation counts.
- Historical data trends.

```markdown
# Citation Statistics

**Last updated:** 2024-07-21

## Overall Statistics
- **Total Citations:** 1234 (+10)
- **H-index:** 25

## New Citations Today
- **Paper Title A:** 5 new citations (100 -> 105)
- **Paper Title B:** 5 new citations (50 -> 55)

## Top Papers by Citation
| Paper                 | Citations | Year |
|-----------------------|-----------|------|
| My Awesome Paper 1    | 105       | 2023 |
| Another Great Paper   | 55        | 2022 |
...
```

## Customization

### Report Format
To change the content or layout of the markdown report, edit `src/markdown_writer.py`.

### Update Frequency
Modify the `cron` schedule in `.github/workflows/update_citations.yml` to change how often the tracker runs.

## Troubleshooting

### Common Issues

1.  **Rate Limiting**: Google Scholar may temporarily block requests if updated too frequently. The default daily schedule is usually safe. If you encounter errors, check `data/tracker.log` for details.
2.  **GitHub Actions Failures**:
    - **Permissions:** Ensure "Read and write permissions" are enabled for Actions in your repository settings. This allows the workflow to commit the updated data files.
    - **Workflow Not Running:** Check that the `.github/workflows/update_citations.yml` file exists on your main branch. Scheduled actions only run on the default branch.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- [scholarly](https://scholarly.readthedocs.io/) for providing a great interface to Google Scholar.
- GitHub Actions for the powerful automation.
