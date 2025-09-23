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
    AUTHOR_CANON, update_author_canon, get_author_canon,
    year_from_date, parse_author_ids, build_author_or_query,
    extract_authors_from_search_item, extract_title_from_result,
    extract_eid_from_result, extract_doi_from_result,
    extract_affiliations_like, extract_author_keywords_from_search_item,
    render_authors, debug_author_canonicalization,
    analyze_output_duplicates, comprehensive_author_statistics,
    extract_abstract_from_result, extract_orcid_id_from_result
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
    required_cols = {"author_id", "start_date", "end_date"}
    if not required_cols.issubset(set(df.columns)):
        raise ValueError("Input CSV must have columns: author_id,start_date,end_date")

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

    first_row = df.iloc[0]
    start_year = year_from_date(first_row.get("start_date", "1900-01-01"))
    end_year = year_from_date(first_row.get("end_date", "2100-12-31"))

    query = build_author_or_query(author_ids, start_year, end_year)
    if args.debug:
        print("Your query builds to:\n", query)
        
    srch = ElsSearch(query, "scopus")
    try:
        srch.execute(client, get_all=True, view="COMPLETE")
    except TypeError:
        # older elsapy signatures
        srch.execute(client, get_all=True)

    if args.debug:
        print(f"[DEBUG] Found {len(srch.results)} search results")

    # PASS 1: Build author canon
    print("Building author canonical names...")
    all_results: List[Dict[str, Any]] = []
    seen_eids: set[str] = set()
    for item in srch.results:
        eid = extract_eid_from_result(item) or ""
        if eid in seen_eids:
            continue
        seen_eids.add(eid)
        
        authors_raw = extract_authors_from_search_item(item)

        title = extract_title_from_result(item) or ""
        abstract = extract_abstract_from_result(item) or ""
        source_title = item.get("prism:publicationName") or ""
        cited_by = item.get("citedby-count") or item.get("citedbyCount") or ""
        doc_type = item.get("subtypeDescription") or item.get("prism:aggregationType") or ""
        doi = extract_doi_from_result(item) or ""
        
        # year
        year: Optional[int] = None
        for k in ("prism:coverDate", "coverDate", "prism:coverDisplayDate", "prism:coverYear"):
            val = item.get(k)
            if not val:
                continue
            try:
                year = int(val) if k == "prism:coverYear" else pd.to_datetime(str(val)).year
                break
            except Exception:
                continue

        affiliations = extract_affiliations_like(item, author_delim)
        author_keywords = extract_author_keywords_from_search_item(item, author_delim)
        
        all_results.append({
            "eid": eid,
            "title": title,
            "year": year or "",
            "abstract": abstract,
            "source_title": source_title,
            "cited_by": cited_by,
            "doc_type": doc_type,
            "doi": doi,
            "affiliations": affiliations,
            "author_keywords": author_keywords,
            "authors_raw": authors_raw,
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
                "Authors","Author full names","Author(s) ID","Title","Year", "Abstract", "Source title",
                "Cited by","DOI","Affiliations","Author Keywords","Index Keywords","Document Type","Source","EID",
            ],
        )
        writer.writeheader()

        for result in all_results:
            a, b, c = render_authors(result["authors_raw"], author_delim)
            writer.writerow({
                "Authors": a,
                "Author full names": b,
                "Author(s) ID": c,
                "Title": result["title"],
                "Year": result["year"],
                "Abstract": result["abstract"],
                "Source title": result["source_title"],
                "Cited by": result["cited_by"],
                "DOI": result["doi"],
                "Affiliations": result["affiliations"],
                "Author Keywords": result["author_keywords"],
                "Document Type": result["doc_type"],
                "Source": "Scopus",
                "EID": result["eid"],
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

