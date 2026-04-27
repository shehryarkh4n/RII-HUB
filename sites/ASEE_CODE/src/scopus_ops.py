from typing import List, Dict, Any, Optional
import time
import math

class ScopusBatcher:
    """
    Handles high-volume Scopus API queries by batching requests
    to stay within URL length limits and optimize throughput.
    """
    
    def __init__(self, api_client=None, batch_size: int = 25):
        self.client = api_client
        self.batch_size = batch_size

    def build_or_query(self, ids: List[str]) -> str:
        """Constructs a single boolean OR query for a list of IDs."""
        if not ids:
            return ""
        clauses = [f"AU-ID({x})" for x in ids]
        return " OR ".join(clauses)

    def fetch_authors_batched(self, author_ids: List[str], mock_mode: bool = False) -> List[Dict]:
        """
        Splits a large list of Author IDs into safe batches and queries Scopus.
        
        Args:
            author_ids: List of numeric Scopus Author IDs.
            mock_mode: If True, returns dummy data instead of hitting API.
        """
        all_results = []
        total_batches = math.ceil(len(author_ids) / self.batch_size)
        
        print(f"Processing {len(author_ids)} IDs in {total_batches} batches...")

        for i in range(total_batches):
            batch = author_ids[i * self.batch_size : (i + 1) * self.batch_size]
            query = self.build_or_query(batch)
            
            print(f"  [Batch {i+1}/{total_batches}] Query length: {len(query)} chars")
            
            if mock_mode or not self.client:
                # Simulate API latency
                time.sleep(0.1) 
                # Generate dummy results
                batch_results = [{"eid": f"2-s2.0-{aid}", "dc:title": f"Paper by {aid}"} for aid in batch]
            else:
                try:
                    # In a real scenario, we would import ElsSearch here
                    # from elsapy.elssearch import ElsSearch
                    # srch = ElsSearch(query, 'scopus')
                    # srch.execute(self.client, get_all=True)
                    # batch_results = srch.results
                    batch_results = [] # Placeholder for demo without library
                    print("    (API Client not provided, skipping actual call)")
                except Exception as e:
                    print(f"    Error in batch {i+1}: {e}")
                    batch_results = []

            all_results.extend(batch_results)
            
        return all_results
