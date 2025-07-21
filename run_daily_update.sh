#!/bin/bash

# A script to automate the process of updating citation data and committing the changes.
#
# This script should be run from the root of the repository.
# To run it daily, you can set up a cron job.
# Example cron job to run daily at midnight and log output:
# 0 0 * * * /path/to/scholar_tracker/run_daily_update.sh >> /path/to/scholar_tracker/update.log 2>&1

echo "========================================"
echo "Starting citation update: $(date)"
echo "========================================"

# Navigate to the script's directory to ensure git and python commands work correctly.
cd "$(dirname "$0")"

# Optional: If you use a Python virtual environment, activate it first.
# For example:
# source venv/bin/activate

# --- IMPORTANT ---
# If you run this on a server, you will likely face the same "403 Forbidden"
# error from Google Scholar that you saw in GitHub Actions.
# To solve this, you need to use a proxy. The line below shows how you would
# set the API key for a service like ScraperAPI.
#
# export SCRAPER_API_KEY="YOUR_SCRAPER_API_KEY_HERE"
#
# For the key to be used, the proxy logic needs to be present in `run.py`.
# If you need help re-adding this logic, just ask!
# -----------------

# Run the Python script to update the data.
echo "--> Running tracker to fetch latest data..."
python3 run.py
echo "--> Tracker finished."


# Configure git user. This is important for running scripts via cron.
git config user.name "Scholar Tracker Bot"
git config user.email "bot@example.com"

# Check for changes in the 'data' directory.
echo "--> Checking for changes..."
if git diff --quiet data/; then
    echo "No changes detected in the data directory. Nothing to commit."
else
    echo "Changes detected. Committing and pushing to remote repository..."
    # Add all changes in the data directory
    git add data/

    # Commit the changes with a timestamp
    git commit -m "Automated citation update: $(date)"

    # Push the changes
    git push

    echo "--> Successfully pushed changes to remote."
fi

echo "========================================"
echo "Update process finished: $(date)"
echo "========================================" 