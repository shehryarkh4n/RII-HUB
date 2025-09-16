from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from dateutil import parser as dtparser

# -------------------------
# Output folder helper
# -------------------------
def make_output_dir(subfolder: str = "uncategorized") -> Path:
    """
    Create (if needed) and return a local output directory relative to the
    *current working directory* (i.e., where the script is called from).

    Example:
        out_dir = make_output_dir()                          # ./local_outputs/uncategorized
        out_dir = make_output_dir("literature_reviews")      # ./local_outputs/literature_reviews

    Returns:
        Path of the created/existing folder.
    """
    base = Path.cwd() / "local_outputs"
    target = base / (subfolder or "uncategorized")
    target.mkdir(parents=True, exist_ok=True)
    return target


# -------------------------
# Canon store
# -------------------------
AUTHOR_CANON: Dict[str, Dict[str, str]] = {}

def _alpha_count(s: str) -> int:
    return sum(1 for ch in (s or "") if ch.isalpha())

def _prefer_given(old: str, new: str) -> str:
    if "." in (new or "") and "." not in (old or ""): return new
    if len(new or "") > len(old or ""): return new
    return old

def update_author_canon(auid: str, surname: str, given: str, initials: str) -> None:
    if not auid: return
    cur = AUTHOR_CANON.get(auid)
    if not cur:
        AUTHOR_CANON[auid] = {"surname": surname, "given": given, "initials": initials}
        return
    if not cur.get("surname") and surname: cur["surname"] = surname
    if _alpha_count(initials) > _alpha_count(cur.get("initials", "")): cur["initials"] = initials
    cur["given"] = _prefer_given(cur.get("given", ""), given)

def get_author_canon(auid: str, surname: str, given: str, initials: str) -> Tuple[str,str,str]:
    c = AUTHOR_CANON.get(auid)
    if not c: return surname, given, initials
    return (c.get("surname") or surname, c.get("given") or given, c.get("initials") or initials)


# -------------------------
# Small helpers
# -------------------------
def year_from_date(s: str) -> int:
    return dtparser.parse(s).year

def parse_author_ids(cell: str) -> List[str]:
    if not cell: return []
    tmp = cell.replace(",", ";").replace("\t", ";").replace("|", ";")
    parts = [p.strip() for p in tmp.split(";")]
    ids: List[str] = []
    for p in parts:
        if not p: continue
        ids.extend([q for q in p.split() if q])
    return [x for x in ids if x.isdigit()]

def build_author_or_query(author_ids: List[str], start_year: int, end_year: int) -> str:
    ors = " OR ".join([f"AU-ID({aid})" for aid in author_ids])
    return f"( {ors} ) AND PUBYEAR > {start_year} AND PUBYEAR < {end_year}"

def _punctuated_initials(initials_raw: Optional[str]) -> str:
    if not initials_raw: return ""
    s = str(initials_raw).strip()
    if "." in s or "-" in s: return s.replace(" ", "")
    out = []
    for ch in s:
        if ch.isalpha(): out.append(ch.upper()); out.append(".")
        elif ch == "-": out.append("-")
    return "".join(out)


# -------------------------
# Field extractors
# -------------------------
def extract_authors_from_search_item(item: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    block = item.get("author") or item.get("authors") or item.get("dc:creator")
    if isinstance(block, list):
        for a in block:
            if not isinstance(a, dict): continue
            auid = str(a.get("authid") or a.get("@auid") or "").strip()
            pref = a.get("preferred-name") or {}
            surname = (pref.get("ce:surname") or a.get("surname") or "").strip()
            given = (pref.get("ce:given-name") or a.get("given-name") or "").strip()
            initials = _punctuated_initials(pref.get("ce:initials") or a.get("initials") or "")
            if auid or surname or given:
                update_author_canon(auid, surname, given, initials)
                out.append({"auid": auid, "surname": surname, "given": given, "initials": initials})
    elif isinstance(block, str):
        parts = [p.strip() for p in block.split(";") if p.strip()]
        for p in parts:
            out.append({"auid": "", "surname": p, "given": "", "initials": ""})
    return out

def extract_affiliations_like(data: Dict[str, Any], delim: str) -> str:
    affs = []
    block = data.get("affiliation") or data.get("affiliations")
    if isinstance(block, list):
        for a in block:
            if not isinstance(a, dict): continue
            name = a.get("affilname") or a.get("affiliation-name") or ""
            city = a.get("affiliation-city") or a.get("city") or ""
            state = a.get("affiliation-state") or a.get("state") or ""
            country = a.get("affiliation-country") or a.get("country") or ""
            parts = [p for p in [name, city, state, country] if p]
            if parts: affs.append(", ".join(parts))
    elif isinstance(block, dict):
        name = block.get("affilname") or block.get("affiliation-name") or ""
        city = block.get("affiliation-city") or block.get("city") or ""
        state = block.get("affiliation-state") or block.get("state") or ""
        country = block.get("affiliation-country") or block.get("country") or ""
        parts = [p for p in [name, city, state, country] if p]
        if parts: affs.append(", ".join(parts))
    return delim.join(affs)

def extract_author_keywords_from_search_item(item: Dict[str, Any], delim: str) -> str:
    ak = item.get("authkeywords")
    if not ak: return ""
    if isinstance(ak, str):
        parts = [p.strip() for p in ak.split("|")]
        parts = [p for p in parts if p]
        return delim.join(parts)
    if isinstance(ak, dict):
        inner = ak.get("value") or ak.get("author-keyword") or ak.get("author_keyword") or []
        vals: List[str] = []
        if isinstance(inner, list):
            for it in inner:
                if isinstance(it, dict):
                    v = it.get("$") or it.get("ce:keyword") or it.get("keyword")
                    if v: vals.append(str(v))
                elif isinstance(it, str): vals.append(it)
        elif isinstance(inner, dict):
            v = inner.get("$") or inner.get("ce:keyword") or inner.get("keyword")
            if v: vals.append(str(v))
        return delim.join(vals)
    return ""

def extract_title_from_result(item: Dict[str, Any]) -> Optional[str]:
    for k in ("dc:title", "title", "prism:title"):
        v = item.get(k)
        if v: return v
    return None

def extract_abstract_from_result(item: Dict[str, Any]) -> Optional[str]:
    abstract = item.get("dc:description")
    if abstract: return abstract
    return None

def extract_eid_from_result(item: Dict[str, Any]) -> Optional[str]:
    for k in ("eid", "scopus-eid"):
        v = item.get(k)
        if v: return v
    v = item.get("dc:identifier")
    if v: return v
    return None

def extract_doi_from_result(item: Dict[str, Any]) -> str:
    return (item.get("prism:doi") or item.get("doi") or "")

def render_authors(authors_raw: List[Dict[str,str]], author_delim: str) -> Tuple[str,str,str]:
    scopus_style_parts: List[str] = []
    full_names: List[str] = []
    ids: List[str] = []
    for a in authors_raw:
        auid = a.get("auid", "")
        s_obs, g_obs, i_obs = a.get("surname", ""), a.get("given", ""), a.get("initials", "")
        s, g, i = get_author_canon(auid, s_obs, g_obs, i_obs)
        parts = []
        if i: parts.append(i)
        parts.append(s)
        if g: parts.append(g)
        scopus_style_parts.append(", ".join(parts))
        full = s
        if g: full += f", {g}"
        if auid: full += f" ({auid})"
        full_names.append(full)
        if auid: ids.append(auid)
    return (author_delim.join(scopus_style_parts),
            author_delim.join(full_names),
            author_delim.join(ids))


# -------------------------
# Debug / validation helpers
# -------------------------
def debug_author_canonicalization(debug: bool = False) -> None:
    """Print detailed canonicalization stats and potential duplicates."""
    if not debug:
        return
    
    print(f"\n[CANON DEBUG] Total authors in canon: {len(AUTHOR_CANON)}")
    
    surname_groups: Dict[str, List[Dict[str, str]]] = {}
    potential_duplicates = []
    
    for auid, data in AUTHOR_CANON.items():
        surname = data.get("surname", "").lower().strip()
        given = data.get("given", "").lower().strip()
        initials = data.get("initials", "").strip()
        
        if not surname:
            continue
            
        key = surname
        surname_groups.setdefault(key, []).append({
            "auid": auid,
            "surname": data.get("surname", ""),
            "given": data.get("given", ""),
            "initials": data.get("initials", "")
        })
    
    for surname, authors in surname_groups.items():
        if len(authors) > 1:
            for i in range(len(authors)):
                for j in range(i+1, len(authors)):
                    a1, a2 = authors[i], authors[j]
                    g1, g2 = a1["given"], a2["given"]
                    i1, i2 = a1["initials"], a2["initials"]
                    
                    suspicious = False
                    reason = ""
                    
                    if g1 and i2 and not g2:
                        if g1.upper().startswith(i2.replace(".", "").replace(" ", "")):
                            suspicious = True
                            reason = "Full name vs matching initials"
                    elif g2 and i1 and not g1:
                        if g2.upper().startswith(i1.replace(".", "").replace(" ", "")):
                            suspicious = True
                            reason = "Full name vs matching initials"
                    elif g1 and g2:
                        if g1.lower() == g2.lower():
                            suspicious = True
                            reason = "Identical given names"
                        elif (len(g1) > 3 and len(g2) > 3 and 
                              (g1.lower().startswith(g2.lower()[:3]) or 
                               g2.lower().startswith(g1.lower()[:3]))):
                            suspicious = True
                            reason = "Similar given names"
                    elif i1 and i2:
                        clean_i1 = i1.replace(".", "").replace(" ", "").upper()
                        clean_i2 = i2.replace(".", "").replace(" ", "").upper()
                        if clean_i1 == clean_i2:
                            suspicious = True
                            reason = "Identical initials"
                    
                    if suspicious:
                        potential_duplicates.append((a1, a2, reason))
    
    if potential_duplicates:
        print(f"\n[CANON DEBUG] Found {len(potential_duplicates)} potential duplicate pairs:")
        for a1, a2, reason in potential_duplicates[:10]:
            print(f"  POTENTIAL DUP ({reason}):")
            print(f"    {a1['auid']}: {a1['surname']}, {a1['given']} ({a1['initials']})")
            print(f"    {a2['auid']}: {a2['surname']}, {a2['given']} ({a2['initials']})")
        if len(potential_duplicates) > 10:
            print(f"  ... and {len(potential_duplicates) - 10} more potential duplicates")
    else:
        print("\n[CANON DEBUG] No obvious potential duplicates found")

def analyze_output_duplicates(csv_path: str) -> bool:
    """Analyze the output CSV for author name duplicates. Returns True if clean."""
    from collections import defaultdict
    
    print(f"\n[OUTPUT ANALYSIS] Reading {csv_path}")
    df_check = pd.read_csv(csv_path)
    
    all_authors = set()
    author_id_to_names = defaultdict(set)
    
    for _, row in df_check.iterrows():
        authors_str = row.get("Authors", "")
        ids_str = row.get("Author(s) ID", "")
        
        if not authors_str or not ids_str:
            continue
            
        authors = [a.strip() for a in str(authors_str).split(";") if a.strip()]
        ids = [i.strip() for i in str(ids_str).split(";") if i.strip()]
        
        for i, author_name in enumerate(authors):
            all_authors.add(author_name)
            if i < len(ids):
                author_id = ids[i]
                author_id_to_names[author_id].add(author_name)
    
    print(f"[OUTPUT ANALYSIS] Total unique author name strings: {len(all_authors)}")
    print(f"[OUTPUT ANALYSIS] Total unique author IDs: {len(author_id_to_names)}")
    
    multi_name_ids = {aid: names for aid, names in author_id_to_names.items() if len(names) > 1}
    if multi_name_ids:
        print(f"\n[OUTPUT ANALYSIS] Found {len(multi_name_ids)} author IDs with multiple name variants:")
        for aid, names in list(multi_name_ids.items())[:10]:
            print(f"  ID {aid}:")
            for name in names:
                print(f"    '{name}'")
        if len(multi_name_ids) > 10:
            print(f"  ... and {len(multi_name_ids) - 10} more")
        return False
    else:
        print("\n[OUTPUT ANALYSIS] All author IDs have consistent names - no duplicates detected!")
        return True

def comprehensive_author_statistics(all_results: List[Dict], csv_path: str, debug: bool = False) -> None:
    """Comprehensive statistics to verify data integrity."""
    if not debug:
        return
    
    print("\n" + "="*60)
    print("COMPREHENSIVE AUTHOR STATISTICS")
    print("="*60)
    
    raw_author_occurrences = 0
    raw_unique_auids = set()
    raw_auids_with_names: Dict[str, List[str]] = {}
    papers_with_authors = 0
    
    for result in all_results:
        authors = result.get("authors_raw", [])
        if authors:
            papers_with_authors += 1
        
        for author in authors:
            raw_author_occurrences += 1
            auid = author.get("auid", "")
            if auid:
                raw_unique_auids.add(auid)
                surname = author.get("surname", "")
                given = author.get("given", "")
                initials = author.get("initials", "")
                name_variant = f"{surname}, {given} ({initials})"
                raw_auids_with_names.setdefault(auid, [])
                if name_variant not in raw_auids_with_names[auid]:
                    raw_auids_with_names[auid].append(name_variant)
    
    print(f"RAW DATA (from Scopus API):")
    print(f"  Total papers processed: {len(all_results)}")
    print(f"  Papers with authors: {papers_with_authors}")
    print(f"  Total author occurrences: {raw_author_occurrences}")
    print(f"  Unique Author IDs found: {len(raw_unique_auids)}")
    
    # 2. Canon integrity vs raw
    canon_auids = set(AUTHOR_CANON.keys())
    canon_vs_raw_missing = raw_unique_auids - canon_auids
    canon_vs_raw_extra = canon_auids - raw_unique_auids
    
    print(f"\nCANONICAL DATA:")
    print(f"  Authors in canon: {len(AUTHOR_CANON)}")
    print(f"  Canon missing raw IDs: {len(canon_vs_raw_missing)} {list(canon_vs_raw_missing)[:3] if canon_vs_raw_missing else ''}")
    print(f"  Canon has extra IDs: {len(canon_vs_raw_extra)} {list(canon_vs_raw_extra)[:3] if canon_vs_raw_extra else ''}")
    
    # 3. Raw name variants (pre-canonicalization)
    auids_with_multiple_variants = {auid: variants for auid, variants in raw_auids_with_names.items() if len(variants) > 1}
    print(f"\nRAW NAME VARIANTS (before canonicalization):")
    print(f"  Author IDs with multiple name variants: {len(auids_with_multiple_variants)}")
    if auids_with_multiple_variants:
        print("  Examples:")
        for auid, variants in list(auids_with_multiple_variants.items())[:3]:
            print(f"    {auid}:")
            for variant in variants:
                print(f"      '{variant}'")
    
    # 4. Output CSV analysis
    df = pd.read_csv(csv_path)
    from collections import defaultdict
    output_author_occurrences = 0
    output_unique_auids = set()
    output_auids_with_names = defaultdict(set)
    
    for _, row in df.iterrows():
        authors_str = row.get("Authors", "")
        ids_str = row.get("Author(s) ID", "")
        if not authors_str or not ids_str:
            continue
        authors = [a.strip() for a in str(authors_str).split(";") if a.strip()]
        ids = [i.strip() for i in str(ids_str).split(";") if i.strip()]
        output_author_occurrences += len(authors)
        for i, author_name in enumerate(authors):
            if i < len(ids):
                author_id = ids[i]
                output_unique_auids.add(author_id)
                output_auids_with_names[author_id].add(author_name)
    
    print(f"\nOUTPUT CSV ANALYSIS:")
    print(f"  Total author occurrences in output: {output_author_occurrences}")
    print(f"  Unique Author IDs in output: {len(output_unique_auids)}")
    print(f"  Unique author name strings: {len(set(name for names in output_auids_with_names.values() for name in names))}")
    
    # 5. Data integrity checks
    raw_vs_output_missing = raw_unique_auids - output_unique_auids
    raw_vs_output_extra = output_unique_auids - raw_unique_auids
    
    print(f"\nDATA INTEGRITY CHECKS:")
    print(f"  Raw IDs missing from output: {len(raw_vs_output_missing)} {list(raw_vs_output_missing)[:3] if raw_vs_output_missing else ''}")
    print(f"  Output has extra IDs not in raw: {len(raw_vs_output_extra)} {list(raw_vs_output_extra)[:3] if raw_vs_output_extra else ''}")
    print(f"  Author occurrence count change: {output_author_occurrences - raw_author_occurrences}")
    
    # 6. Canonicalization effectiveness
    output_duplicates = {aid: names for aid, names in output_auids_with_names.items() if len(names) > 1}
    canonicalization_success_rate = (len(raw_unique_auids) - len(output_duplicates)) / len(raw_unique_auids) * 100 if raw_unique_auids else 0
    
    print(f"\nCANONICALIZATION EFFECTIVENESS:")
    print(f"  Raw IDs with multiple variants: {len(auids_with_multiple_variants)}")
    print(f"  Output IDs with multiple variants: {len(output_duplicates)}")
    print(f"  Successfully canonicalized: {len(auids_with_multiple_variants) - len(output_duplicates)}")
    print(f"  Canonicalization success rate: {canonicalization_success_rate:.1f}%")
    
    # 7. Final verification
    print(f"\nFINAL VERIFICATION:")
    all_checks_passed = True
    
    if raw_vs_output_missing:
        print(f" LOST {len(raw_vs_output_missing)} author IDs from raw to output")
        all_checks_passed = False
    else:
        print(f" No author IDs lost")
    
    if raw_vs_output_extra:
        print(f" GAINED {len(raw_vs_output_extra)} unexpected author IDs in output")
        all_checks_passed = False
    else:
        print(f" No unexpected author IDs added")
    
    if output_author_occurrences != raw_author_occurrences:
        print(f" Author occurrence count changed by {output_author_occurrences - raw_author_occurrences}")
        all_checks_passed = False
    else:
        print(f" Author occurrence count preserved")
    
    if len(output_unique_auids) != len(raw_unique_auids):
        print(f" Unique author count changed from {len(raw_unique_auids)} to {len(output_unique_auids)}")
        all_checks_passed = False
    else:
        print(f" Unique author count preserved ({len(output_unique_auids)})")
    
    if output_duplicates:
        print(f" {len(output_duplicates)} author IDs still have multiple name variants")
    else:
        print(f" Perfect canonicalization - no duplicate names")
    
    if all_checks_passed and not output_duplicates:
        print(f"\nPERFECT: All data integrity checks passed AND canonicalization is perfect!")
    elif all_checks_passed:
        print(f"\nGOOD: Data integrity maintained, minor canonicalization issues remain")
    else:
        print(f"\nISSUES: Data integrity problems detected - review above")
    
    print("="*60)
