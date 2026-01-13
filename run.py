import os
import json
import logging
from src.scholar_tracker import ScholarTracker
from src.markdown_writer import MarkdownWriter
from src.chart_generator import ChartGenerator

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_summary():
    """Print a colored summary of today's changes."""
    history_file = "data/citation_history.json"
    changes_file = "data/daily_changes.json"

    if not os.path.exists(history_file):
        return

    with open(history_file, 'r') as f:
        history = json.load(f)

    if not history:
        return

    latest = history[-1]
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}        CITATION TRACKER SUMMARY{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.END}\n")

    # Overall stats
    print(f"{Colors.BOLD}Overall Statistics:{Colors.END}")
    print(f"  Total Citations:  {Colors.BLUE}{latest['total_citations']}{Colors.END}")
    print(f"  H-index:          {Colors.BLUE}{latest['h_index']}{Colors.END}")
    print(f"  Total Papers:     {Colors.BLUE}{len(latest['papers'])}{Colors.END}")

    # Recent growth
    if len(history) > 1:
        prev = history[-2]
        growth = latest['total_citations'] - prev['total_citations']
        growth_color = Colors.GREEN if growth > 0 else Colors.RED if growth < 0 else ""
        print(f"  Recent Growth:    {growth_color}{'+' if growth > 0 else ''}{growth}{Colors.END}")

    # Today's changes
    if os.path.exists(changes_file):
        with open(changes_file, 'r') as f:
            daily_changes = json.load(f)
        if daily_changes:
            latest_changes = daily_changes[-1]
            if latest_changes["date"] == latest["date"]:
                increase = latest_changes['total_citations_increase']
                if increase > 0:
                    print(f"\n{Colors.BOLD}{Colors.GREEN}Today's Changes: +{increase} citations{Colors.END}")
                    for paper in latest_changes["papers_with_changes"]:
                        print(f"  {Colors.YELLOW}+{paper['increase']}{Colors.END} {paper['title']}")
                else:
                    print(f"\n{Colors.BOLD}{Colors.CYAN}Today's Changes: No new citations{Colors.END}")
            else:
                print(f"\n{Colors.BOLD}{Colors.CYAN}No data for today yet{Colors.END}")

    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*50}{Colors.END}\n")

def print_readme():
    """Print the contents of data/README.md with highlighted changes."""
    readme_path = "data/README.md"
    if not os.path.exists(readme_path):
        return

    with open(readme_path, 'r') as f:
        content = f.read()

    # Highlight sections
    lines = content.split('\n')
    for line in lines:
        if line.startswith('#'):
            print(f"{Colors.HEADER}{line}{Colors.END}")
        elif line.startswith('|'):
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if '+' in line and any('+-' in col for col in cols):
                # Highlight positive changes
                print(f"{Colors.GREEN}{line}{Colors.END}")
            elif 'Recent Citation Growth' in line or "Today's Changes" in line:
                print(f"{Colors.YELLOW}{line}{Colors.END}")
            else:
                print(line)
        elif '- Total Citations Increase:' in line or ('citations:' in line and '+' in line and not 'Total' in line):
            print(f"{Colors.GREEN}{line}{Colors.END}")
        else:
            print(line)
    print()

def main():
    # Note: The ScholarTracker now has built-in fallback to manual HTML parsing
    # when the scholarly library fails, so no need for complex proxy setup

    # Initialize tracker with author ID
    tracker = ScholarTracker(author_id="VtK5lwUAAAAJ")

    # Update citation history
    if tracker.update_history():
        print("Successfully updated citation history")

        # Generate charts
        chart_gen = ChartGenerator(
            data_file="data/citation_history.json",
            output_dir="data"
        )
        chart_gen.generate_charts()
        print("Successfully generated charts")

        # Initialize markdown writer
        writer = MarkdownWriter(
            data_file="data/citation_history.json",
            output_file="data/citations.md"
        )

        # Generate reports
        success = all([
            writer.generate_markdown(),
            writer.generate_data_readme()
        ])

        if success:
            print("Successfully generated all reports")
        else:
            print("Failed to generate some reports")

        # Print colored summary
        print_summary()

        # Print README with highlighting
        print(f"{Colors.BOLD}Full Report:{Colors.END}")
        print_readme()

    else:
        print("Failed to update citation history")
        # print the error
        # print(tracker.error)

if __name__ == "__main__":
    main()
