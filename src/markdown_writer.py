from datetime import datetime
import json
import os

class MarkdownWriter:
    def __init__(self, data_file, output_file):
        self.data_file = data_file
        self.output_file = output_file
        self.data_dir = os.path.dirname(output_file)
        
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
                "\n## Paper Citations",
                "\n| Paper | Citations | Year |",
                "| ----- | --------- | ---- |"
            ]
            
            # Add paper stats
            for paper in latest['papers']:
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
                f"| Total Papers | {total_papers} |",
                f"| Recent Citation Growth | {citation_growth:+d} |",
                
                "\n## Citation Trends",
                "\n### Overall Citation Metrics",
                "![Citation Trends](citation_trends.png)",
                "\n### Individual Paper Performance",
                "![Paper Trends](paper_trends.png)",
                
                "\n## Top Papers",
                "\n| Paper | Citations | Year |",
                "| ----- | --------- | ---- |"
            ]
            
            # Add top 5 papers by citation count
            sorted_papers = sorted(
                latest['papers'], 
                key=lambda x: x['citations'], 
                reverse=True
            )
            for paper in sorted_papers[:5]:
                content.append(
                    f"| {paper['title']} | {paper['citations']} | {paper['year']} |"
                )
                
            # Add links to detailed reports
            content.extend([
                "\n## Detailed Reports",
                "- [Full Citation Report](citations.md)",
                "- [Interactive Overall Trends](citation_trends.html)",
                "- [Interactive Paper Trends](paper_trends.html)",
                
                "\n## Directory Contents",
                "- `citations.md`: Detailed daily citation report",
                "- `citation_history.json`: Raw historical data",
                "- `citation_trends.png/.html`: Overall citation trend visualizations",
                "- `paper_trends.png/.html`: Individual paper trend visualizations",
                
                "\n---",
                "*This report is automatically generated and updated daily*"
            ])
            
            # Write to README.md in data directory
            readme_path = os.path.join(self.data_dir, 'README.md')
            with open(readme_path, 'w') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            print(f"Error generating data README: {e}")
            return False