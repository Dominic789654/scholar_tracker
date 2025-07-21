from src.scholar_tracker import ScholarTracker
from src.markdown_writer import MarkdownWriter
from src.chart_generator import ChartGenerator
import os
from scholarly import scholarly, ProxyGenerator

def main():
    # Configure ScraperAPI proxy if API key is available
    scraper_api_key = os.getenv("SCRAPER_API_KEY")
    if scraper_api_key:
        print("ScraperAPI key found, setting up proxy...")
        pg = ProxyGenerator()
        success = pg.ScraperAPI(scraper_api_key)
        if success:
            scholarly.use_proxy(pg)
            print("Successfully configured ScraperAPI proxy.")
        else:
            print("Failed to configure ScraperAPI proxy. Continuing without proxy.")

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