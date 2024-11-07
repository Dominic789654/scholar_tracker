from datetime import datetime
import json

class MarkdownWriter:
    def __init__(self, data_file, output_file):
        self.data_file = data_file
        self.output_file = output_file
        
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
                
            # Write to file
            with open(self.output_file, 'w') as f:
                f.write('\n'.join(content))
                
            return True
            
        except Exception as e:
            print(f"Error generating markdown: {e}")
            return False 