from src.scholar_tracker import ScholarTracker
from src.markdown_writer import MarkdownWriter

def main():
    # Initialize tracker with your scholar search query
    tracker = ScholarTracker("Xiang Liu HKUST")
    
    # Update citation history
    if tracker.update_history():
        print("Successfully updated citation history")
        
        # Generate markdown report
        writer = MarkdownWriter(
            data_file="data/citation_history.json",
            output_file="data/citations.md"
        )
        
        if writer.generate_markdown():
            print("Successfully generated markdown report")
        else:
            print("Failed to generate markdown report")
    else:
        print("Failed to update citation history")

if __name__ == "__main__":
    main() 