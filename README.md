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

## GitHub Actions Setup Guide

### 1. Enable GitHub Actions

1. Go to your repository on GitHub
2. Click on "Settings" tab
3. Scroll down to "Actions" section in the left sidebar
4. Under "Actions permissions":
   - Select "Allow all actions and reusable workflows"
   - Click "Save"

### 2. Configure Repository Permissions

GitHub Actions needs permission to push changes back to your repository:

1. Still in repository Settings
2. Go to "Actions" → "General" in the left sidebar
3. Scroll down to "Workflow permissions"
4. Enable "Read and write permissions"
5. Check "Allow GitHub Actions to create and approve pull requests"
6. Click "Save"

### 3. Configure Repository Secrets (Optional)

If you need to use any sensitive data (like API keys):

1. Go to repository Settings
2. Click on "Secrets and variables" → "Actions" in the left sidebar
3. Click "New repository secret"
4. Add your secrets (if needed)

### 4. Verify Setup

1. Go to the "Actions" tab in your repository
2. You should see the workflow "Update Citations"
3. Click on "Run workflow" → "Run workflow" to trigger manually
4. Check if the workflow runs successfully

### Troubleshooting Actions

If your workflow fails, check these common issues:

1. **Permission Errors**
   ```bash
   ! [remote rejected] main -> main (refusing to allow an OAuth App to create or update workflow)
   ```
   Solution: Double-check steps 1 and 2 above for permissions

2. **Workflow Not Visible**
   - Ensure `.github/workflows/update_citations.yml` is in the main branch
   - Check if Actions is enabled in repository settings

3. **Push Errors**
   ```bash
   ! [remote rejected] HEAD -> main (refusing to allow an OAuth App to create or update workflow)
   ```
   Solution:
   - Go to Settings → Actions → General
   - Scroll to "Workflow permissions"
   - Enable "Read and write permissions"

4. **Scheduled Runs Not Working**
   - Note that scheduled runs only work on the default branch
   - First manual run may be needed to initialize
   - Check your timezone vs UTC for cron schedule

### Visual Guide

Here's where to find key settings:

```
Repository
└── Settings
    ├── Actions
    │   ├── General
    │   │   ├── Actions permissions
    │   │   └── Workflow permissions
    │   └── Secrets and variables
    └── Pages (if you want to publish results)
```

### Testing Your Setup

1. Make a small change to your repository
2. Push the change
3. Go to the "Actions" tab
4. You should see your workflow running
5. After completion, check:
   - `data/citations.md` for updated stats
   - `data/citation_history.json` for historical data

### Monitoring

- Go to "Actions" tab to see all workflow runs
- Click on any run to see detailed logs
- Enable notifications in repository settings to get alerts on workflow failures

### Best Practices

1. **Always test locally first**
   ```bash
   python run.py
   ```

2. **Start with manual triggers**
   - Use `workflow_dispatch` before setting up scheduled runs
   - Helps identify issues before automation

3. **Monitor initial runs**
   - Watch the first few automated runs
   - Check logs for any warnings or errors

4. **Version Control**
   - Keep your workflow file versioned
   - Document any changes in commit messages
