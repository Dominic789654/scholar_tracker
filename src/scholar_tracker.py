from scholarly import scholarly
from datetime import datetime
import json
import os

class ScholarTracker:
    def __init__(self, author_query):
        self.author_query = author_query
        self.data_file = "data/citation_history.json"
        
    def get_author_stats(self):
        """Retrieve author statistics from Google Scholar"""
        try:
            # Search for author
            search_query = scholarly.search_author(self.author_query)
            author = scholarly.fill(next(search_query))
            
            # Get current date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Collect stats
            stats = {
                "date": today,
                "total_citations": author.get('citedby', 0),
                "h_index": author.get('hindex', 0),
                "papers": []
            }
            
            # Collect individual paper stats
            for pub in author.get('publications', []):
                paper = {
                    "title": pub['bib']['title'],
                    "citations": pub.get('num_citations', 0),
                    "year": pub['bib'].get('pub_year', 'N/A')
                }
                stats["papers"].append(paper)
                
            return stats
            
        except Exception as e:
            print(f"Error fetching scholar data: {e}")
            return None
            
    def update_history(self):
        """Update citation history with new data"""
        stats = self.get_author_stats()
        if not stats:
            return False
            
        # Load existing history
        history = []
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                history = json.load(f)
                
        # Add new stats
        history.append(stats)
        
        # Save updated history
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        return True 