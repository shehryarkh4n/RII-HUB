# from __future__ import annotations
# import argparse, csv, os
# from pathlib import Path
# from typing import Dict, List, Any, Optional, Tuple
# import pandas as pd
# from dateutil import parser as dtparser
# from dotenv import load_dotenv
# from elsapy.elsclient import ElsClient
# from elsapy.elssearch import ElsSearch

# def debug_author_canonicalization(debug: bool = False) -> None:
#     """Print detailed canonicalization stats and potential duplicates."""
#     if not debug:
#         return
    
#     print(f"\n[CANON DEBUG] Total authors in canon: {len(AUTHOR_CANON)}")
    
#     # Check for potential duplicates by name similarity
#     surname_groups = {}
#     potential_duplicates = []
    
#     for auid, data in AUTHOR_CANON.items():
#         surname = data.get("surname", "").lower().strip()
#         given = data.get("given", "").lower().strip()
#         initials = data.get("initials", "").strip()
        
#         if not surname:
#             continue
            
#         key = surname
#         if key not in surname_groups:
#             surname_groups[key] = []
#         surname_groups[key].append({
#             "auid": auid,
#             "surname": data.get("surname", ""),
#             "given": data.get("given", ""),
#             "initials": data.get("initials", "")
#         })
    
#     # Find surname groups with multiple authors
#     for surname, authors in surname_groups.items():
#         if len(authors) > 1:
#             # Check if they might be the same person
#             for i in range(len(authors)):
#                 for j in range(i+1, len(authors)):
#                     a1, a2 = authors[i], authors[j]
                    
#                     # Same surname, check given names/initials
#                     g1, g2 = a1["given"], a2["given"]
#                     i1, i2 = a1["initials"], a2["initials"]
                    
#                     suspicious = False
#                     reason = ""
                    
#                     # Case 1: One has full name, other has initials that match
#                     if g1 and i2 and not g2:
#                         if g1.upper().startswith(i2.replace(".", "").replace(" ", "")):
#                             suspicious = True
#                             reason = "Full name vs matching initials"
#                     elif g2 and i1 and not g1:
#                         if g2.upper().startswith(i1.replace(".", "").replace(" ", "")):
#                             suspicious = True
#                             reason = "Full name vs matching initials"
                    
#                     # Case 2: Both have given names that are similar
#                     elif g1 and g2:
#                         if g1.lower() == g2.lower():
#                             suspicious = True
#                             reason = "Identical given names"
#                         elif (len(g1) > 3 and len(g2) > 3 and 
#                               (g1.lower().startswith(g2.lower()[:3]) or 
#                                g2.lower().startswith(g1.lower()[:3]))):
#                             suspicious = True
#                             reason = "Similar given names"
                    
#                     # Case 3: Both have initials that match
#                     elif i1 and i2:
#                         clean_i1 = i1.replace(".", "").replace(" ", "").upper()
#                         clean_i2 = i2.replace(".", "").replace(" ", "").upper()
#                         if clean_i1 == clean_i2:
#                             suspicious = True
#                             reason = "Identical initials"
                    
#                     if suspicious:
#                         potential_duplicates.append((a1, a2, reason))
    
#     if potential_duplicates:
#         print(f"\n[CANON DEBUG] Found {len(potential_duplicates)} potential duplicate pairs:")
#         for a1, a2, reason in potential_duplicates[:10]:  # Show first 10
#             print(f"  POTENTIAL DUP ({reason}):")
#             print(f"    {a1['auid']}: {a1['surname']}, {a1['given']} ({a1['initials']})")
#             print(f"    {a2['auid']}: {a2['surname']}, {a2['given']} ({a2['initials']})")
#         if len(potential_duplicates) > 10:
#             print(f"  ... and {len(potential_duplicates) - 10} more potential duplicates")
#     else:
#         print("\n[CANON DEBUG] No obvious potential duplicates found")

# def analyze_output_duplicates(csv_path: str) -> bool:
#     """Analyze the output CSV for author name duplicates. Returns True if clean."""
#     from collections import defaultdict
    
#     print(f"\n[OUTPUT ANALYSIS] Reading {csv_path}")
#     df_check = pd.read_csv(csv_path)
    
#     # Extract all unique author names and IDs
#     all_authors = set()
#     author_id_to_names = defaultdict(set)
    
#     for _, row in df_check.iterrows():
#         authors_str = row.get("Authors", "")
#         ids_str = row.get("Author(s) ID", "")
        
#         if not authors_str or not ids_str:
#             continue
            
#         authors = [a.strip() for a in authors_str.split(";") if a.strip()]
#         ids = [i.strip() for i in ids_str.split(";") if i.strip()]
        
#         # Match authors to IDs (assuming same order)
#         for i, author_name in enumerate(authors):
#             all_authors.add(author_name)
#             if i < len(ids):
#                 author_id = ids[i]
#                 author_id_to_names[author_id].add(author_name)
    
#     print(f"[OUTPUT ANALYSIS] Total unique author name strings: {len(all_authors)}")
#     print(f"[OUTPUT ANALYSIS] Total unique author IDs: {len(author_id_to_names)}")
    
#     # Find IDs with multiple name variants
#     multi_name_ids = {aid: names for aid, names in author_id_to_names.items() if len(names) > 1}
#     if multi_name_ids:
#         print(f"\n[OUTPUT ANALYSIS] Found {len(multi_name_ids)} author IDs with multiple name variants:")
#         for aid, names in list(multi_name_ids.items())[:10]:  # Show first 10
#             print(f"  ID {aid}:")
#             for name in names:
#                 print(f"    '{name}'")
#         if len(multi_name_ids) > 10:
#             print(f"  ... and {len(multi_name_ids) - 10} more")
#         return False
#     else:
#         print("\n[OUTPUT ANALYSIS] All author IDs have consistent names - no duplicates detected!")
#         return True
    
# def comprehensive_author_statistics(all_results: List[Dict], csv_path: str, debug: bool = False) -> None:
#     """Comprehensive statistics to verify data integrity."""
#     if not debug:
#         return
    
#     print("\n" + "="*60)
#     print("COMPREHENSIVE AUTHOR STATISTICS")
#     print("="*60)
    
#     # 1. Count raw author occurrences across all papers
#     raw_author_occurrences = 0
#     raw_unique_auids = set()
#     raw_auids_with_names = {}  # auid -> list of name variants seen
#     papers_with_authors = 0
    
#     for result in all_results:
#         authors = result.get("authors_raw", [])
#         if authors:
#             papers_with_authors += 1
        
#         for author in authors:
#             raw_author_occurrences += 1
#             auid = author.get("auid", "")
#             if auid:
#                 raw_unique_auids.add(auid)
#                 surname = author.get("surname", "")
#                 given = author.get("given", "")
#                 initials = author.get("initials", "")
#                 name_variant = f"{surname}, {given} ({initials})"
                
#                 if auid not in raw_auids_with_names:
#                     raw_auids_with_names[auid] = []
#                 if name_variant not in raw_auids_with_names[auid]:
#                     raw_auids_with_names[auid].append(name_variant)
    
#     print(f"RAW DATA (from Scopus API):")
#     print(f"  Total papers processed: {len(all_results)}")
#     print(f"  Papers with authors: {papers_with_authors}")
#     print(f"  Total author occurrences: {raw_author_occurrences}")
#     print(f"  Unique Author IDs found: {len(raw_unique_auids)}")
#     print(f"  Authors without IDs: {raw_author_occurrences - sum(len(authors) for authors in [r.get('authors_raw', []) for r in all_results] for a in authors if a.get('auid'))}")
    
#     # 2. Check canonical data integrity
#     canon_auids = set(AUTHOR_CANON.keys())
#     canon_vs_raw_missing = raw_unique_auids - canon_auids
#     canon_vs_raw_extra = canon_auids - raw_unique_auids
    
#     print(f"\nCANONICAL DATA:")
#     print(f"  Authors in canon: {len(AUTHOR_CANON)}")
#     print(f"  Canon missing raw IDs: {len(canon_vs_raw_missing)} {list(canon_vs_raw_missing)[:3] if canon_vs_raw_missing else ''}")
#     print(f"  Canon has extra IDs: {len(canon_vs_raw_extra)} {list(canon_vs_raw_extra)[:3] if canon_vs_raw_extra else ''}")
    
#     # 3. Analyze raw name variants before canonicalization
#     auids_with_multiple_variants = {auid: variants for auid, variants in raw_auids_with_names.items() if len(variants) > 1}
#     print(f"\nRAW NAME VARIANTS (before canonicalization):")
#     print(f"  Author IDs with multiple name variants: {len(auids_with_multiple_variants)}")
#     if auids_with_multiple_variants:
#         print("  Examples:")
#         for auid, variants in list(auids_with_multiple_variants.items())[:3]:
#             print(f"    {auid}:")
#             for variant in variants:
#                 print(f"      '{variant}'")
    
#     # 4. Analyze output CSV
#     import pandas as pd
#     from collections import defaultdict, Counter
    
#     df = pd.read_csv(csv_path)
    
#     # Count author occurrences in output
#     output_author_occurrences = 0
#     output_unique_auids = set()
#     output_auids_with_names = defaultdict(set)
    
#     for _, row in df.iterrows():
#         authors_str = row.get("Authors", "")
#         ids_str = row.get("Author(s) ID", "")
        
#         if not authors_str or not ids_str:
#             continue
        
#         authors = [a.strip() for a in authors_str.split(";") if a.strip()]
#         ids = [i.strip() for i in ids_str.split(";") if i.strip()]
        
#         output_author_occurrences += len(authors)
        
#         for i, author_name in enumerate(authors):
#             if i < len(ids):
#                 author_id = ids[i]
#                 output_unique_auids.add(author_id)
#                 output_auids_with_names[author_id].add(author_name)
    
#     print(f"\nOUTPUT CSV ANALYSIS:")
#     print(f"  Total author occurrences in output: {output_author_occurrences}")
#     print(f"  Unique Author IDs in output: {len(output_unique_auids)}")
#     print(f"  Unique author name strings: {len(set(name for names in output_auids_with_names.values() for name in names))}")
    
#     # 5. Data integrity checks
#     raw_vs_output_missing = raw_unique_auids - output_unique_auids
#     raw_vs_output_extra = output_unique_auids - raw_unique_auids
    
#     print(f"\nDATA INTEGRITY CHECKS:")
#     print(f"  Raw IDs missing from output: {len(raw_vs_output_missing)} {list(raw_vs_output_missing)[:3] if raw_vs_output_missing else ''}")
#     print(f"  Output has extra IDs not in raw: {len(raw_vs_output_extra)} {list(raw_vs_output_extra)[:3] if raw_vs_output_extra else ''}")
#     print(f"  Author occurrence count change: {output_author_occurrences - raw_author_occurrences}")
    
#     # 6. Canonicalization effectiveness
#     output_duplicates = {aid: names for aid, names in output_auids_with_names.items() if len(names) > 1}
#     canonicalization_success_rate = (len(raw_unique_auids) - len(output_duplicates)) / len(raw_unique_auids) * 100 if raw_unique_auids else 0
    
#     print(f"\nCANONICALIZATION EFFECTIVENESS:")
#     print(f"  Raw IDs with multiple variants: {len(auids_with_multiple_variants)}")
#     print(f"  Output IDs with multiple variants: {len(output_duplicates)}")
#     print(f"  Successfully canonicalized: {len(auids_with_multiple_variants) - len(output_duplicates)}")
#     print(f"  Canonicalization success rate: {canonicalization_success_rate:.1f}%")
    
#     # 7. Final verification
#     print(f"\nFINAL VERIFICATION:")
#     all_checks_passed = True
    
#     if raw_vs_output_missing:
#         print(f" LOST {len(raw_vs_output_missing)} author IDs from raw to output")
#         all_checks_passed = False
#     else:
#         print(f" No author IDs lost")
    
#     if raw_vs_output_extra:
#         print(f" GAINED {len(raw_vs_output_extra)} unexpected author IDs in output")
#         all_checks_passed = False
#     else:
#         print(f" No unexpected author IDs added")
    
#     if output_author_occurrences != raw_author_occurrences:
#         print(f" Author occurrence count changed by {output_author_occurrences - raw_author_occurrences}")
#         all_checks_passed = False
#     else:
#         print(f" Author occurrence count preserved")
    
#     if len(output_unique_auids) != len(raw_unique_auids):
#         print(f" Unique author count changed from {len(raw_unique_auids)} to {len(output_unique_auids)}")
#         all_checks_passed = False
#     else:
#         print(f" Unique author count preserved ({len(output_unique_auids)})")
    
#     if output_duplicates:
#         print(f" {len(output_duplicates)} author IDs still have multiple name variants")
#     else:
#         print(f" Perfect canonicalization - no duplicate names")
    
#     if all_checks_passed and not output_duplicates:
#         print(f"\nPERFECT: All data integrity checks passed AND canonicalization is perfect!")
#     elif all_checks_passed:
#         print(f"\nGOOD: Data integrity maintained, minor canonicalization issues remain")
#     else:
#         print(f"\nISSUES: Data integrity problems detected - review above")
    
#     print("="*60)

# def year_from_date(s: str) -> int:
#     return dtparser.parse(s).year

# def parse_author_ids(cell: str) -> List[str]:
#     if not cell: return []
#     tmp = cell.replace(",", ";").replace("\t", ";").replace("|", ";")
#     parts = [p.strip() for p in tmp.split(";")]
#     ids: List[str] = []
#     for p in parts:
#         if not p: continue
#         ids.extend([q for q in p.split() if q])
#     return [x for x in ids if x.isdigit()]

# def build_author_or_query(author_ids: List[str], start_year: int, end_year: int) -> str:
#     ors = " OR ".join([f"AU-ID({aid})" for aid in author_ids])
#     return f"( {ors} ) AND PUBYEAR > {start_year} AND PUBYEAR < {end_year}"

# AUTHOR_CANON: Dict[str, Dict[str, str]] = {}

# def _alpha_count(s: str) -> int:
#     return sum(1 for ch in (s or "") if ch.isalpha())

# def _prefer_given(old: str, new: str) -> str:
#     if "." in (new or "") and "." not in (old or ""): return new
#     if len(new or "") > len(old or ""): return new
#     return old

# def update_author_canon(auid: str, surname: str, given: str, initials: str) -> None:
#     if not auid: return
#     cur = AUTHOR_CANON.get(auid)
#     if not cur:
#         AUTHOR_CANON[auid] = {"surname": surname, "given": given, "initials": initials}
#         return
#     if not cur.get("surname") and surname: cur["surname"] = surname
#     if _alpha_count(initials) > _alpha_count(cur.get("initials", "")): cur["initials"] = initials
#     cur["given"] = _prefer_given(cur.get("given", ""), given)

# def get_author_canon(auid: str, surname: str, given: str, initials: str) -> Tuple[str,str,str]:
#     c = AUTHOR_CANON.get(auid)
#     if not c: return surname, given, initials
#     return (c.get("surname") or surname, c.get("given") or given, c.get("initials") or initials)

# def _punctuated_initials(initials_raw: Optional[str]) -> str:
#     if not initials_raw: return ""
#     s = str(initials_raw).strip()
#     if "." in s or "-" in s: return s.replace(" ", "")
#     out = []
#     for ch in s:
#         if ch.isalpha(): out.append(ch.upper()); out.append(".")
#         elif ch == "-": out.append("-")
#     return "".join(out)

# def extract_authors_from_search_item(item: Dict[str, Any]) -> List[Dict[str, str]]:
#     out: List[Dict[str, str]] = []
#     block = item.get("author") or item.get("authors") or item.get("dc:creator")
#     if isinstance(block, list):
#         for a in block:
#             if not isinstance(a, dict): continue
#             auid = str(a.get("authid") or a.get("@auid") or "").strip()
#             pref = a.get("preferred-name") or {}
#             surname = (pref.get("ce:surname") or a.get("surname") or "").strip()
#             given = (pref.get("ce:given-name") or a.get("given-name") or "").strip()
#             initials = _punctuated_initials(pref.get("ce:initials") or a.get("initials") or "")
#             if auid or surname or given:
#                 update_author_canon(auid, surname, given, initials)
#                 out.append({"auid": auid, "surname": surname, "given": given, "initials": initials})
#     elif isinstance(block, str):
#         parts = [p.strip() for p in block.split(";") if p.strip()]
#         for p in parts:
#             out.append({"auid": "", "surname": p, "given": "", "initials": ""})
#     return out

# def extract_affiliations_like(data: Dict[str, Any], delim: str) -> str:
#     affs = []
#     block = data.get("affiliation") or data.get("affiliations")
#     if isinstance(block, list):
#         for a in block:
#             if not isinstance(a, dict): continue
#             name = a.get("affilname") or a.get("affiliation-name") or ""
#             city = a.get("affiliation-city") or a.get("city") or ""
#             state = a.get("affiliation-state") or a.get("state") or ""
#             country = a.get("affiliation-country") or a.get("country") or ""
#             parts = [p for p in [name, city, state, country] if p]
#             if parts: affs.append(", ".join(parts))
#     elif isinstance(block, dict):
#         name = block.get("affilname") or block.get("affiliation-name") or ""
#         city = block.get("affiliation-city") or block.get("city") or ""
#         state = block.get("affiliation-state") or block.get("state") or ""
#         country = block.get("affiliation-country") or block.get("country") or ""
#         parts = [p for p in [name, city, state, country] if p]
#         if parts: affs.append(", ".join(parts))
#     return delim.join(affs)

# def extract_author_keywords_from_search_item(item: Dict[str, Any], delim: str) -> str:
#     ak = item.get("authkeywords")
#     if not ak: return ""
#     if isinstance(ak, str):
#         parts = [p.strip() for p in ak.split("|")]
#         parts = [p for p in parts if p]
#         return delim.join(parts)
#     if isinstance(ak, dict):
#         inner = ak.get("value") or ak.get("author-keyword") or ak.get("author_keyword") or []
#         vals: List[str] = []
#         if isinstance(inner, list):
#             for it in inner:
#                 if isinstance(it, dict):
#                     v = it.get("$") or it.get("ce:keyword") or it.get("keyword")
#                     if v: vals.append(str(v))
#                 elif isinstance(it, str): vals.append(it)
#         elif isinstance(inner, dict):
#             v = inner.get("$") or inner.get("ce:keyword") or inner.get("keyword")
#             if v: vals.append(str(v))
#         return delim.join(vals)
#     return ""

# def extract_title_from_result(item: Dict[str, Any]) -> Optional[str]:
#     for k in ("dc:title", "title", "prism:title"):
#         v = item.get(k)
#         if v: return v
#     return None

# def extract_eid_from_result(item: Dict[str, Any]) -> Optional[str]:
#     for k in ("eid", "scopus-eid"):
#         v = item.get(k)
#         if v: return v
#     v = item.get("dc:identifier")
#     if v: return v
#     return None

# def extract_scp_id_from_result(item: Dict[str, Any]) -> Optional[str]:
#     dcid = item.get("dc:identifier")
#     if isinstance(dcid, str) and "SCOPUS_ID:" in dcid:
#         return dcid.split("SCOPUS_ID:")[-1].strip()
#     eid = item.get("eid")
#     if isinstance(eid, str) and eid.count("-") >= 2:
#         return eid.split("-")[-1].strip()
#     sid = item.get("scopus-id")
#     if sid: return str(sid).strip()
#     return None

# def extract_doi_from_result(item: Dict[str, Any]) -> str:
#     return (item.get("prism:doi") or item.get("doi") or "")

# def render_authors(authors_raw: List[Dict[str,str]], author_delim: str) -> Tuple[str,str,str]:
#     scopus_style_parts: List[str] = []
#     full_names: List[str] = []
#     ids: List[str] = []
#     for a in authors_raw:
#         auid = a.get("auid", "")
#         s_obs, g_obs, i_obs = a.get("surname", ""), a.get("given", ""), a.get("initials", "")
#         s, g, i = get_author_canon(auid, s_obs, g_obs, i_obs)
#         parts = []
#         if i: parts.append(i)
#         parts.append(s)
#         if g: parts.append(g)
#         scopus_style_parts.append(", ".join(parts))
#         full = s
#         if g: full += f", {g}"
#         if auid: full += f" ({auid})"
#         full_names.append(full)
#         if auid: ids.append(auid)
#     return (author_delim.join(scopus_style_parts),
#             author_delim.join(full_names),
#             author_delim.join(ids))

# def main():
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--in", dest="in_csv", required=True)
#     ap.add_argument("--out", dest="out_csv", required=True)
#     ap.add_argument("--debug", action="store_true")
#     args = ap.parse_args()

#     load_dotenv()
#     api_key = os.getenv("ELSEVIER_API_KEY")
#     if not api_key: raise ValueError("Missing ELSEVIER_API_KEY")
#     author_delim = os.getenv("AUTHOR_DELIM", "; ")

#     client = ElsClient(api_key)

#     df = pd.read_csv(args.in_csv, dtype=str)
#     df.columns = [c.lower() for c in df.columns]
#     required_cols = {"author_id", "start_date", "end_date"}
#     if not required_cols.issubset(set(df.columns)): raise ValueError("Input CSV must have columns: author_id,start_date,end_date")

#     all_author_ids: List[str] = []
#     for _, r in df.iterrows():
#         all_author_ids.extend(parse_author_ids((r.get("author_id") or "").strip()))
#     seen = set()
#     author_ids = [x for x in all_author_ids if not (x in seen or seen.add(x))]
#     if not author_ids:
#         Path(args.out_csv).write_text("")
#         return

#     first_row = df.iloc[0]
#     start_year = year_from_date(first_row.get("start_date", "1900-01-01"))
#     end_year = year_from_date(first_row.get("end_date", "2100-12-31"))

#     query = build_author_or_query(author_ids, start_year, end_year)
#     if args.debug: print("Your query builds to:\n", query)
    
#     srch = ElsSearch(query, "scopus")
#     try:
#         srch.execute(client, get_all=True, view="COMPLETE")
#     except TypeError:
#         srch.execute(client, get_all=True)

#     if args.debug:
#         print(f"[DEBUG] Found {len(srch.results)} search results")

#     # PASS 1: Build complete author canon by processing all results
#     print("Building author canonical names...")
#     all_results = []
#     seen_eids: set[str] = set()
    
#     for item in srch.results:
#         eid = extract_eid_from_result(item) or ""
#         if eid in seen_eids: continue
#         seen_eids.add(eid)
        
#         # Extract authors and update canon (don't render yet)
#         authors_raw = extract_authors_from_search_item(item)
        
#         # Store all the data we need for later
#         title = extract_title_from_result(item) or ""
#         source_title = item.get("prism:publicationName") or ""
#         cited_by = item.get("citedby-count") or item.get("citedbyCount") or ""
#         doc_type = item.get("subtypeDescription") or item.get("prism:aggregationType") or ""
#         doi = extract_doi_from_result(item) or ""
        
#         year: Optional[int] = None
#         for k in ("prism:coverDate", "coverDate", "prism:coverDisplayDate", "prism:coverYear"):
#             val = item.get(k)
#             if not val: continue
#             try:
#                 year = int(val) if k == "prism:coverYear" else dtparser.parse(str(val)).year
#                 break
#             except Exception:
#                 continue

#         affiliations = extract_affiliations_like(item, author_delim)
#         author_keywords = extract_author_keywords_from_search_item(item, author_delim)
        
#         all_results.append({
#             "eid": eid,
#             "title": title,
#             "year": year or "",
#             "source_title": source_title,
#             "cited_by": cited_by,
#             "doc_type": doc_type,
#             "doi": doi,
#             "affiliations": affiliations,
#             "author_keywords": author_keywords,
#             "authors_raw": authors_raw,
#         })

#     debug_author_canonicalization(args.debug)

#     # PASS 2: Now render all authors using the complete canon
#     print("Generating output with canonical names...")
#     out_path = Path(args.out_csv)
#     out_path.parent.mkdir(parents=True, exist_ok=True)
    
#     with open(out_path, "w", newline="", encoding="utf-8") as f:
#         writer = csv.DictWriter(
#             f,
#             fieldnames=[
#                 "Authors","Author full names","Author(s) ID","Title","Year","Source title",
#                 "Cited by","DOI","Affiliations","Author Keywords","Index Keywords","Document Type","Source","EID",
#             ],
#         )
#         writer.writeheader()

#         for result in all_results:
#             # Now render using the complete canon
#             a, b, c = render_authors(result["authors_raw"], author_delim)
#             writer.writerow({
#                 "Authors": a,
#                 "Author full names": b,
#                 "Author(s) ID": c,
#                 "Title": result["title"],
#                 "Year": result["year"],
#                 "Source title": result["source_title"],
#                 "Cited by": result["cited_by"],
#                 "DOI": result["doi"],
#                 "Affiliations": result["affiliations"],
#                 "Author Keywords": result["author_keywords"],
#                 "Document Type": result["doc_type"],
#                 "Source": "Scopus",
#                 "EID": result["eid"],
#             })

#     print(f"Wrote {len(all_results)} rows to {out_path}")
    
#     if args.debug:
#         comprehensive_author_statistics(all_results, str(out_path), debug=True)
#     else:
#         # Quick check for non-debug runs
#         is_clean = analyze_output_duplicates(str(out_path))
#         if is_clean:
#             print("No author duplicates detected!")

# if __name__ == "__main__":
#     main()
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
    analyze_output_duplicates, comprehensive_author_statistics
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
                "Authors","Author full names","Author(s) ID","Title","Year","Source title",
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

