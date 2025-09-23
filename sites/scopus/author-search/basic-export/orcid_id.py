from __future__ import annotations
import argparse, os, csv
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from dotenv import load_dotenv
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

from utils import (
    # output helper
    make_output_dir,
    # canon + helpers
    extract_author_id_from_author_search,
    parse_author_ids, debug_author_canonicalization,
    analyze_output_duplicates, comprehensive_author_statistics,
    extract_orcid_id_from_result, build_author_or_query,
    extract_surname_preferred_name_author_search
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True, help="Input CSV with columns: author_id,start_date,end_date")
    ap.add_argument("--out", dest="out_csv", required=False, help="Optional explicit output CSV path")
    ap.add_argument("--subfolder", dest="subfolder", default="uncategorized",
                    help="Optional subfolder inside ./local_outputs (default: 'uncategorized')")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    # env / client
    load_dotenv()
    api_key = os.getenv("ELSEVIER_API_KEY")
    if not api_key:
        raise ValueError("Missing ELSEVIER_API_KEY")
    author_delim = os.getenv("AUTHOR_DELIM", "; ")

    client = ElsClient(api_key)

    # read input
    df = pd.read_csv(args.in_csv, dtype=str)
    df.columns = [c.lower() for c in df.columns]
    required_cols = {"author_id"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError("Input CSV must have columns: author_id")

    # author ids
    all_author_ids: List[str] = []
    for _, r in df.iterrows():
        all_author_ids.extend(parse_author_ids((r.get("author_id") or "").strip()))
    seen = set()
    author_ids = [x for x in all_author_ids if not (x in seen or seen.add(x))]
    if not author_ids:
        # ensure output file exists (even empty)
        out_csv = Path(args.out_csv) if args.out_csv else (make_output_dir(args.subfolder) / "results.csv")
        out_csv.write_text("")
        print(f"No author IDs found. Wrote empty file to {out_csv}")
        return

    query = build_author_or_query(author_ids)
    
    if args.debug:
        print("Your query builds to:\n", query)
        
    srch = ElsSearch(query, "author")
    srch.execute(client, get_all=True)

    if args.debug:
        print(f"[DEBUG] Found {len(srch.results)} search results")
    
        
    # PASS 1: Build author canon
    print("Building author canonical names...")
    all_results: List[Dict[str, Any]] = []
    for item in srch.results:
        surname, given_name = extract_surname_preferred_name_author_search(item) or ""
        orcid_id = extract_orcid_id_from_result(item) or ""
        author_id = extract_author_id_from_author_search(item) or ""
        all_results.append({
            "surname": surname,
            "given_name": given_name,
            "orcid_id": orcid_id,
            "author_id": author_id
        })

    debug_author_canonicalization(args.debug)

    # Determine output path
    if args.out_csv:
        out_path = Path(args.out_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = make_output_dir(args.subfolder)  # <-- auto-create ./local_outputs/<subfolder>
        out_path = out_dir / "results.csv"

    # PASS 2: Render with canon and write
    print("Generating output with canonical names...")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Last Name", "First Name", "Author ID", "ORCiD"
            ],
        )
        writer.writeheader()

        for result in all_results:
            writer.writerow({
                "Last Name": result["surname"],
                "First Name": result["given_name"],
                "Author ID": result["author_id"],
                "ORCiD": result["orcid_id"]
            })

    print(f"Wrote {len(all_results)} rows to {out_path}")
    
    if args.debug:
        comprehensive_author_statistics(all_results, str(out_path), debug=True)
    else:
        is_clean = analyze_output_duplicates(str(out_path))
        if is_clean:
            print("No author duplicates detected!")

if __name__ == "__main__":
    main()

