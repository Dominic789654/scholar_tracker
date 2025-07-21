from src.scholar_tracker import ScholarTracker
from src.markdown_writer import MarkdownWriter
from src.chart_generator import ChartGenerator
import os
from scholarly import scholarly, ProxyGenerator

def main():
    # Configure ScraperAPI proxy if API key is available

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
    else:
        print("Failed to update citation history")
        # print the error
        # print(tracker.error)
        
if __name__ == "__main__":
    main() 