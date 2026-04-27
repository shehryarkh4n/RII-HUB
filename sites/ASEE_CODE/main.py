import pandas as pd
from src.scopus_ops import ScopusBatcher
from src.institution_matcher import InstitutionMatcher
from src.utils import generate_name_variants

def demo_scopus_batching():
    print("\n" + "="*50)
    print("DEMO 1: Optimized Scopus Batch Querying")
    print("="*50)
    
    # Simulate a list of 60 author IDs (normally this would be huge)
    fake_ids = [str(10000000 + i) for i in range(60)]
    
    # Initialize batcher (batch_size=25 to demonstrate splitting)
    batcher = ScopusBatcher(batch_size=25)
    
    # Run (in mock mode for demo)
    results = batcher.fetch_authors_batched(fake_ids, mock_mode=True)
    
    print(f"Total results fetched: {len(results)}")
    print("Sample result:", results[0] if results else "None")

def demo_institution_matching():
    print("\n" + "="*50)
    print("DEMO 2: Intelligent Institutional Alignment")
    print("="*50)
    
    # Reference Data (Official List)
    official_list = {
        "1001": "Virginia Polytechnic Institute and State University",
        "1002": "University of California, Berkeley",
        "1003": "Texas A&M University"
    }
    
    matcher = InstitutionMatcher(official_list)
    
    # Test Cases
    test_inputs = [
        "Virginia Tech",                     # Common alias
        "Va. Polytechnic Inst.",             # Abbreviation
        "Univ. of Calif. Berkeley",          # Abbreviation + punctuation
        "Texas A and M",                     # & vs and
        "Virginia Tech Carilion Med School"  # Tricky case
    ]
    
    print(f"{ 'Input String':<35} | { 'Match ID':<10} | { 'Method':<20} | { 'Score'}")
    print("-" * 85)
    
    for inp in test_inputs:
        uid, method, score = matcher.match(inp)
        print(f"{inp:<35} | {str(uid):<10} | {method:<20} | {score}")

def demo_name_generation():
    print("\n" + "="*50)
    print("DEMO 3: Recursive Name Variant Generation")
    print("="*50)
    
    surname = "Van der Waals"
    given = "Johannes Diderik"
    
    variants = generate_name_variants(surname, given)
    
    print(f"Input: {surname}, {given}")
    print("Generated Variants for Search/Matching:")
    for v in sorted(variants):
        print(f" - {v}")

def main():
    print("ASEE CODE REPOSITORY DEMO")
    print("Showcasing core functionalities for Research Identity Management")
    
    demo_scopus_batching()
    demo_institution_matching()
    demo_name_generation()

if __name__ == "__main__":
    main()
