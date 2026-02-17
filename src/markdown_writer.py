from datetime import datetime
import json
import os

class MarkdownWriter:
    def __init__(self, data_file, output_file):
        self.data_file = data_file
        self.output_file = output_file
        self.data_dir = os.path.dirname(output_file)
        self.daily_changes_file = os.path.join(self.data_dir, "daily_changes.json")
        
    def generate_markdown(self):
        """Generate markdown report from citation history"""
        try:
            # Load citation history
            with open(self.data_file, 'r') as f:
                history = json.load(f)
                
            if not history:
                return False
                
            # Get latest stats
            latest = history[-1]
            
            # Generate markdown content
            content = [
                "# Citation Statistics",
                f"\nLast updated: {latest['date']}",
                f"\n## Overall Statistics",
                f"- Total Citations: {latest['total_citations']}",
                f"- H-index: {latest['h_index']}",
                f"- i10-index: {latest.get('i10_index', 'N/A')}"
            ]
            
            # Add today's citation changes if available
            if os.path.exists(self.daily_changes_file):
                with open(self.daily_changes_file, 'r') as f:
                    daily_changes = json.load(f)
                if daily_changes:
                    latest_changes = daily_changes[-1]
                    if latest_changes["date"] == latest["date"] and latest_changes["papers_with_changes"]:
                        content.extend([
                            "\n## Today's Citation Changes ",
                            f"\nTotal increase: +{latest_changes['total_citations_increase']} citations",
                            "\n| Paper | Previous | New | Increase |",
                            "| ----- | --------- | --- | -------- |"
                        ])
                        for paper in latest_changes["papers_with_changes"]:
                            content.append(
                                f"| {paper['title']} | {paper['previous_citations']} | {paper['new_citations']} | +{paper['increase']} |"
                            )
            
            # Add paper stats (sorted by citations descending)
            sorted_papers = sorted(latest['papers'], key=lambda x: x['citations'], reverse=True)
            content.extend([
                "\n## Paper Citations",
                "\n| Paper | Citations | Year |",
                "| ----- | --------- | ---- |"
            ])
            
            # Add paper stats
            for paper in sorted_papers:
                content.append(
                    f"| {paper['title']} | {paper['citations']} | {paper['year']} |"
                )
                
            # Add citation history
            content.extend([
                "\n## Citation History",
                "\n| Date | Total Citations | H-index |",
                "| ---- | --------------- | ------- |"
            ])
            
            for entry in reversed(history[-10:]):  # Show last 10 entries
                content.append(
                    f"| {entry['date']} | {entry['total_citations']} | {entry['h_index']} |"
                )
                
            # Add charts
            content.extend([
                "\n## Citation Trends",
                "\n### Overall Trends",
                "![Citation Trends](citation_trends.png)",
                "\n### Individual Paper Trends",
                "![Paper Trends](paper_trends.png)",
                "\n*For interactive charts, see [citation_trends.html](citation_trends.html) and [paper_trends.html](paper_trends.html)*"
            ])
            
            # Write to file
            with open(self.output_file, 'w') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            print(f"Error generating markdown: {e}")
            return False 
    
    def generate_data_readme(self):
        """Generate README.md for the data directory"""
        try:
            with open(self.data_file, 'r') as f:
                history = json.load(f)
                
            if not history:
                return False
                
            latest = history[-1]
            
            # Calculate some additional statistics
            total_papers = len(latest['papers'])
            citation_growth = 0
            if len(history) > 1:
                prev = history[-2]
                citation_growth = latest['total_citations'] - prev['total_citations']
            
            # Generate content
            content = [
                "# Citation Statistics Overview",
                "\n## Latest Statistics",
                f"*Last Updated: {latest['date']}*",
                "\n### Quick Summary",
                "| Metric | Value |",
                "| ------ | ----- |",
                f"| Total Citations | {latest['total_citations']} |",
                f"| H-index | {latest['h_index']} |",
                f"| i10-index | {latest.get('i10_index', 'N/A')} |",
                f"| Total Papers | {total_papers} |",
                f"| Recent Citation Growth | {'+' if citation_growth > 0 else ''}{citation_growth} |"
            ]
            
            # Add today's changes if available
            if os.path.exists(self.daily_changes_file):
                with open(self.daily_changes_file, 'r') as f:
                    daily_changes = json.load(f)
                if daily_changes:
                    latest_changes = daily_changes[-1]
                    if latest_changes["date"] == latest["date"] and latest_changes["papers_with_changes"]:
                        content.extend([
                            "\n### Today's Changes",
                            f"- Total Citations Increase: +{latest_changes['total_citations_increase']}",
                            "- Papers with new citations:",
                        ])
                        for paper in latest_changes["papers_with_changes"]:
                            content.append(f"  - {paper['title']}: +{paper['increase']} citations")
            
            # Write to file
            readme_path = os.path.join(self.data_dir, "README.md")
            with open(readme_path, 'w') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            print(f"Error generating data README: {e}")
            return False