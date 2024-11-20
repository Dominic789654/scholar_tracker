from scholarly import scholarly
from datetime import datetime
import json
import os

class ScholarTracker:
    def __init__(self, author_query):
        self.author_query = author_query
        self.data_file = "data/citation_history.json"
        self.daily_changes_file = "data/daily_changes.json"
        
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
    
    def get_citation_changes(self, current_stats, previous_stats):
        """Compare current and previous stats to find citation changes"""
        if not previous_stats or not current_stats:
            return None
            
        changes = {
            "date": current_stats["date"],
            "total_citations_increase": current_stats["total_citations"] - previous_stats["total_citations"],
            "papers_with_changes": []
        }
        
        # Create a map of previous paper citations
        prev_citations = {paper["title"]: paper["citations"] for paper in previous_stats["papers"]}
        
        # Check each current paper for changes
        for paper in current_stats["papers"]:
            prev_count = prev_citations.get(paper["title"], 0)
            if paper["citations"] > prev_count:
                changes["papers_with_changes"].append({
                    "title": paper["title"],
                    "previous_citations": prev_count,
                    "new_citations": paper["citations"],
                    "increase": paper["citations"] - prev_count
                })
        
        return changes
            
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
        
        # Get previous day's stats
        previous_stats = history[-1] if history else None
        
        # Calculate citation changes
        if previous_stats:
            changes = self.get_citation_changes(stats, previous_stats)
            if changes and changes["papers_with_changes"]:
                # Load existing changes
                daily_changes = []
                if os.path.exists(self.daily_changes_file):
                    with open(self.daily_changes_file, 'r') as f:
                        daily_changes = json.load(f)
                
                # Add new changes
                daily_changes.append(changes)
                
                # Save updated changes
                os.makedirs(os.path.dirname(self.daily_changes_file), exist_ok=True)
                with open(self.daily_changes_file, 'w') as f:
                    json.dump(daily_changes, f, indent=2)
                
        # Add new stats to history
        history.append(stats)
        
        # Save updated history
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        return True