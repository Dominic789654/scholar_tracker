import logging
from scholarly import scholarly
from datetime import datetime
import json
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("data/tracker.log", mode='a'),
                        logging.StreamHandler()
                    ])

class ScholarTracker:
    def __init__(self, author_query=None, author_id=None):
        if not author_query and not author_id:
            raise ValueError("Either author_query or author_id must be provided.")
        self.author_query = author_query
        self.author_id = author_id
        self.data_file = "data/citation_history.json"
        self.daily_changes_file = "data/daily_changes.json"
        logging.info(f"ScholarTracker initialized for author_query: '{self.author_query}', author_id: '{self.author_id}'")
        
    def get_author_stats(self):
        """Retrieve author statistics from Google Scholar"""
        try:
            author = None
            if self.author_id:
                logging.info(f"Searching for author by ID: '{self.author_id}'")
                author = scholarly.search_author_id(self.author_id, filled=True)
            else:
                logging.info(f"Searching for author by name: '{self.author_query}'")
                search_query = scholarly.search_author(self.author_query)
                author = scholarly.fill(next(search_query))
            
            if not author:
                logging.error(f"Could not find author with ID '{self.author_id}' or query '{self.author_query}'.")
                return None

            logging.info(f"Found author: {author.get('name')}")
            
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
                # The 'bib' key may not exist for all publications, so we use .get()
                bib = pub.get('bib', {})
                paper = {
                    "title": bib.get('title'),
                    "citations": pub.get('num_citations', 0),
                    "year": bib.get('pub_year', 'N/A')
                }
                stats["papers"].append(paper)
                
            logging.info(f"Successfully collected stats for {len(stats['papers'])} papers.")
            return stats
            
        except StopIteration:
            logging.error(f"Author with query '{self.author_query}' not found on Google Scholar.")
            return None
        except Exception as e:
            logging.error(f"Error fetching scholar data: {e}", exc_info=True)
            return None
    
    def get_citation_changes(self, current_stats, previous_stats):
        """Compare current and previous stats to find citation changes"""
        if not previous_stats or not current_stats:
            return None

        logging.info("Calculating citation changes...")
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
        
        if changes["papers_with_changes"]:
            logging.info(f"Found {len(changes['papers_with_changes'])} papers with new citations.")
        else:
            logging.info("No new citations found for any papers.")

        return changes
            
    def update_history(self):
        """Update citation history with new data"""
        logging.info("Starting history update...")
        stats = self.get_author_stats()
        if not stats:
            logging.warning("Aborting history update because fetching stats failed.")
            return False
            
        # Load existing history
        history = []
        if os.path.exists(self.data_file):
            logging.info(f"Loading existing history from {self.data_file}")
            with open(self.data_file, 'r') as f:
                history = json.load(f)
        else:
            logging.info("No history file found. A new one will be created.")

        # Get previous day's stats
        previous_stats = history[-1] if history else None
        
        # Calculate citation changes
        if previous_stats:
            logging.info("Comparing with previous stats to find citation changes.")
            changes = self.get_citation_changes(stats, previous_stats)
            if changes and changes["papers_with_changes"]:
                logging.info("Changes found, updating daily changes file.")
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
                logging.info(f"Saved daily changes to {self.daily_changes_file}")
        else:
            logging.info("No previous stats to compare against.")

        # Add new stats to history
        history.append(stats)
        
        # Save updated history
        logging.info(f"Saving updated history to {self.data_file}")
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        logging.info("History update complete.")
        return True