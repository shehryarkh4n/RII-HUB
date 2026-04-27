from __future__ import annotations
import argparse, os, csv, time, re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Iterable, Set
import pandas as pd

from datetime import datetime
from dotenv import load_dotenv
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch

from utils import (
    read_table, parse_name_column, make_output_dir,
    extract_affiliation_name,
    extract_author_id_from_author_search,
    extract_orcid_id_from_result,
    extract_surname_preferred_name_author_search,
)

def is_empty_result(raw) -> bool:
    return (
        isinstance(raw, list)
        and len(raw) == 1
        and isinstance(raw[0], dict)
        and raw[0].get("error") == "Result set was empty"
    )

def run_author_query(client: ElsClient, surname: str, given: str, affil_q: str,
                     max_retries: int = 3, backoff: float = 1.5) -> List[Dict[str, Any]]:
    """Runs one (authlast & authfirst) AND affiliation query; returns list of results."""
    query = f"(authlast({surname}) and authfirst({given})) AND {affil_q}"
    attempt = 0
    while True:
        try:
            s = ElsSearch(query, "author")
            s.execute(client, get_all=True)
            return s.results or []
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                print(f"[WARN] Query failed for {surname}, {given}: {e}")
                return []
            time.sleep(backoff ** attempt)

def run_au_id_query(client, au_id):
    query = f"AU-ID({au_id})"
    s = ElsSearch(query, "author")
    s.execute(client, get_all=True)
    return s.results or []

# === name normalization helpers =================================================
_WS_PUNCT_RE = re.compile(r"[^\w]+", flags=re.UNICODE)

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = _WS_PUNCT_RE.sub("", s)
    return s

def _initials_of(given: str) -> str:
    toks = [t for t in re.split(r"[\s\-]+", given.strip()) if t]
    initials = "".join(t[0] for t in toks if t)
    return initials

def _variants_for_surname_given(surname: str, given: str) -> Iterable[str]:
    s = (surname or "").strip()
    g = (given or "").strip()
    initials = _initials_of(g)

    raw_variants = set()
    raw_variants.add(f"{s}, {g}")
    if g:
        raw_variants.add(f"{s}, {g[0]}")
        raw_variants.add(f"{s}, {g[0]}.")
    if initials:
        raw_variants.add(f"{s}, {initials}")
        raw_variants.add(f"{s}, {'.'.join(list(initials))}.")
    raw_variants.add(f"{g} {s}")

    for rv in raw_variants:
        yield _norm(rv)

def _build_master_name_index(master: pd.DataFrame,
                             master_name_col: str = "Author Full Name") -> Set[str]:
    idx: Set[str] = set()
    if master_name_col not in master.columns:
        return idx
    for v in master[master_name_col].astype(str).fillna("").tolist():
        v = v.strip()
        if not v:
            continue
        idx.add(_norm(v))
        if "," in v:
            try:
                s, g = [p.strip() for p in v.split(",", 1)]
                idx.add(_norm(f"{g} {s}"))
            except Exception:
                pass
        else:
            parts = v.split()
            if len(parts) >= 2:
                s = parts[-1]
                g = " ".join(parts[:-1])
                idx.add(_norm(f"{s}, {g}"))
    return idx

# NEW: minimal lookup so we can retrieve the single master row (to get Author ID)
def _build_master_name_lookup(master: pd.DataFrame,
                              master_name_col: str = "Author Full Name") -> Dict[str, List[int]]:
    look: Dict[str, List[int]] = {}
    if master_name_col not in master.columns:
        return look
    for i, v in enumerate(master[master_name_col].astype(str).fillna("").tolist()):
        v = v.strip()
        if not v:
            continue
        keys = set()
        keys.add(_norm(v))
        if "," in v:
            try:
                s, g = [p.strip() for p in v.split(",", 1)]
                keys.add(_norm(f"{g} {s}"))
            except Exception:
                pass
        else:
            parts = v.split()
            if len(parts) >= 2:
                s = parts[-1]
                g = " ".join(parts[:-1])
                keys.add(_norm(f"{s}, {g}"))
        for k in keys:
            look.setdefault(k, []).append(i)
    return look

def _scopus_name_from_item(item: Dict[str, Any]) -> Tuple[str, str, str]:
    got_surname, got_given = extract_surname_preferred_name_author_search(item) or ("", "")
    display = f"{(got_surname or '').strip()}, {(got_given or '').strip()}".strip(", ").strip()
    return (got_surname or ""), (got_given or ""), display

# ================================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--ref", dest="ref_csv", required=True)
    ap.add_argument("--out", dest="out_csv", required=False)
    ap.add_argument("--subfolder", dest="subfolder", default="uncategorized")
    ap.add_argument("--affil", dest="affil",
                    default="(AFFIL(Virginia Tech) OR AFFIL(Virginia Polytechnic))",
                    help="Scopus affiliation filter. Replace with your institution's name(s), "
                         "e.g. \"(AFFIL(MIT) OR AFFIL(Massachusetts Institute of Technology))\".")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    api_key = os.getenv("ELSEVIER_API_KEY")
    if not api_key:
        raise ValueError("Missing ELSEVIER_API_KEY")
    client = ElsClient(api_key)

    df = read_table(args.in_csv)
    master = pd.read_csv(args.ref_csv)
    print("TOTAL:", len(df))

    MASTER_NAME_COL = "Author Full Name"  # keep your existing column names
    MASTER_ID_COL   = "Author ID"         # used for AU-ID lookup

    master_name_index  = _build_master_name_index(master, MASTER_NAME_COL)
    master_name_lookup = _build_master_name_lookup(master, MASTER_NAME_COL)  # NEW

    for c in ["ScholarID", "ClientFacultyId", "OrcId", "scholarname"]:
        if c not in df.columns:
            df[c] = ""

    name_tuples: List[Tuple[str, str]] = parse_name_column(df["scholarname"])
    
    # date suffixes
    today_str = datetime.today().strftime("%Y%m%d")

    if args.out_csv:
        # If user specified an output file, insert date before extension
        out_path = Path(args.out_csv)
        stem, suffix = out_path.stem, out_path.suffix
        out_path = out_path.with_name(f"{stem}_{today_str}{suffix}")
    else:
        out_path = make_output_dir(args.subfolder) / f"final_scopus_matches_{today_str}.csv"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ScholarID", "ClientFacultyId", "OrcId",
        "Scopus Last Name", "Scopus First Name", "Scopus ID", "Scopus ORCiD",
        "Status",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in df.reset_index(drop=True).iterrows():
            scholar_id = str(row.get("scholarid", "") or "")
            client_fid = str(row.get("clientfacultyid", "") or "")
            val = row.get("orcid")
            input_orcid = "" if pd.isna(val) else str(val).strip()
            exp_surname, exp_given = name_tuples[i] if i < len(name_tuples) else ("", "")

            if args.debug:
                print(f"\n=== [{i+1}] Searching for: {exp_surname}, {exp_given} (ScholarID={scholar_id}) ===")

            results = run_author_query(client, exp_surname, exp_given, args.affil)
            if args.debug:
                print(f"  -> Scopus returned {len(results)} results")

            if is_empty_result(results) or len(results) == 0:
                if args.debug:
                    print("  -> Empty result set, trying master lookup...")

                # Try variants against master lookup
                variants = list(_variants_for_surname_given(exp_surname, exp_given))
                matched_rows: set[int] = set()
                for v in variants:
                    matched_rows.update(master_name_lookup.get(v, []))

                if len(matched_rows) == 1:
                    m_idx = next(iter(matched_rows))
                    au_id_val = master.iloc[m_idx].get(MASTER_ID_COL, "")
                    au_id = "" if pd.isna(au_id_val) else str(au_id_val).strip()
                    m_name = str(master.iloc[m_idx].get(MASTER_NAME_COL, ""))

                    if args.debug:
                        print(f"  -> Master lookup found unique row: {m_name}, AU-ID={au_id}")

                    writer.writerow({
                        "ScholarID": scholar_id,
                        "ClientFacultyId": client_fid,
                        "OrcId": input_orcid,
                        "Scopus Last Name": exp_surname,
                        "Scopus First Name": exp_given,
                        "Scopus ID": au_id,
                        "Scopus ORCiD": "",
                        "Status": "Match (Master)",
                    })
                    continue

                elif len(matched_rows) > 1:
                    if args.debug:
                        names = master.loc[list(matched_rows), MASTER_NAME_COL].astype(str).tolist()
                        print(f"  -> Multiple master matches: {names}")

                    writer.writerow({
                        "ScholarID": scholar_id,
                        "ClientFacultyId": client_fid,
                        "OrcId": input_orcid,
                        "Scopus Last Name": exp_surname,
                        "Scopus First Name": exp_given,
                        "Scopus ID": "",
                        "Scopus ORCiD": "",
                        "Status": "Ambiguous (Master)",
                    })
                    continue

                # No master fallback either → final no match
                writer.writerow({
                    "ScholarID": scholar_id,
                    "ClientFacultyId": client_fid,
                    "OrcId": input_orcid,
                    "Scopus Last Name": exp_surname,
                    "Scopus First Name": exp_given,
                    "Scopus ID": "",
                    "Scopus ORCiD": "",
                    "Status": "No Match",
                })
                continue

            if len(results) == 1:
                item = results[0]
                got_surname, got_given = extract_surname_preferred_name_author_search(item) or ("", "")
                orcid_id = extract_orcid_id_from_result(item) or ""
                author_id = extract_author_id_from_author_search(item) or ""
                if args.debug:
                    print(f"  -> Single match: {got_surname}, {got_given}, ID={author_id}, ORCID={orcid_id}")
                writer.writerow({
                    "ScholarID": scholar_id,
                    "ClientFacultyId": client_fid,
                    "OrcId": input_orcid,
                    "Scopus Last Name": got_surname,
                    "Scopus First Name": got_given,
                    "Scopus ID": author_id,
                    "Scopus ORCiD": orcid_id,
                    "Status": "Match (Direct)",
                })
                continue

            # Multiple results — try cross-matching with master
            matched_indices: List[int] = []
            master_rows_hit: set[int] = set()  # NEW: track which exact master rows matched

            for idx, item in enumerate(results):
                sname, gname, display = _scopus_name_from_item(item)
                variants = list(_variants_for_surname_given(sname, gname))
                hit = any(v in master_name_index for v in variants)
                # NEW: collect concrete master row hits (so we can fetch Author ID)
                rows_for_candidate = set()
                for v in variants:
                    for r in master_name_lookup.get(v, []):
                        rows_for_candidate.add(r)
                if args.debug:
                    print(f"  -> Candidate {idx+1}: '{display}'")
                    print(f"     Variants: {variants}")
                    print(f"     Found in master? {hit}")
                    if rows_for_candidate:
                        names = master.loc[list(rows_for_candidate), MASTER_NAME_COL].astype(str).tolist()
                        print(f"     Master rows matched ({len(rows_for_candidate)}): {names}")
                    else:
                        print(f"     Master rows matched: 0")
                if hit:
                    matched_indices.append(idx)
                    master_rows_hit.update(rows_for_candidate)

            if len(matched_indices) == 1:
                item = results[matched_indices[0]]
                got_surname, got_given = extract_surname_preferred_name_author_search(item) or ("", "")
                orcid_id = extract_orcid_id_from_result(item) or ""
                author_id = extract_author_id_from_author_search(item) or ""
                if args.debug:
                    print(f"  -> Unique cross-match found: {got_surname}, {got_given}, ID={author_id}")
                writer.writerow({
                    "ScholarID": scholar_id,
                    "ClientFacultyId": client_fid,
                    "OrcId": input_orcid,
                    "Scopus Last Name": got_surname,
                    "Scopus First Name": got_given,
                    "Scopus ID": author_id,
                    "Scopus ORCiD": orcid_id,
                    "Status": "Match (Master)",
                })
                continue

            if len(matched_indices) > 1:
                # NEW: If name matches map to exactly ONE master row, use its Author ID for a tie-breaker
                if len(master_rows_hit) == 1:
                    m_idx = next(iter(master_rows_hit))
                    au_id_val = master.iloc[m_idx].get(MASTER_ID_COL, "")
                    au_id = "" if pd.isna(au_id_val) else str(au_id_val).strip()
                    if args.debug:
                        m_name = str(master.iloc[m_idx].get(MASTER_NAME_COL, ""))
                        print("  -> Multiple Scopus candidates but Master collapses to a single row")
                        print(f"     Master[{m_idx}] {MASTER_NAME_COL}='{m_name}', {MASTER_ID_COL}='{au_id}'")
                    if au_id:
                        try:
                            id_results = run_au_id_query(client, au_id) or []
                        except Exception as e:
                            if args.debug:
                                print(f"  -> ID query failed for AU-ID={au_id}: {e}")
                            id_results = []

                        if is_empty_result(id_results) or len(id_results) == 0:
                            if args.debug:
                                print("  -> ID SEARCH NONE")
                            writer.writerow({
                                "ScholarID": scholar_id,
                                "ClientFacultyId": client_fid,
                                "OrcId": input_orcid,
                                "Scopus Last Name": exp_surname,
                                "Scopus First Name": exp_given,
                                "Scopus ID": "",
                                "Scopus ORCiD": "",
                                "Status": "No Match (ID)",
                            })
                            continue

                        if len(id_results) == 1:
                            item = id_results[0]
                            got_surname, got_given = extract_surname_preferred_name_author_search(item) or ("", "")
                            orcid_id = extract_orcid_id_from_result(item) or ""
                            author_id = extract_author_id_from_author_search(item) or ""
                            if args.debug:
                                print(f"  -> EXACT (ID SEARCH): {got_surname}, {got_given}, ID={author_id}, ORCID={orcid_id}")
                            writer.writerow({
                                "ScholarID": scholar_id,
                                "ClientFacultyId": client_fid,
                                "OrcId": input_orcid,
                                "Scopus Last Name": got_surname,
                                "Scopus First Name": got_given,
                                "Scopus ID": author_id,
                                "Scopus ORCiD": orcid_id,
                                "Status": "Match (ID)",
                            })
                            continue

                        # >1 results from AU-ID (unlikely, but follow your spec)
                        if args.debug:
                            print(f"  -> ID SEARCH MULTIPLE ({len(id_results)} results)")
                        writer.writerow({
                            "ScholarID": scholar_id,
                            "ClientFacultyId": client_fid,
                            "OrcId": input_orcid,
                            "Scopus Last Name": exp_surname,
                            "Scopus First Name": exp_given,
                            "Scopus ID": "",
                            "Scopus ORCiD": "",
                            "Status": "Ambiguous (ID)",
                        })
                        continue
                    else:
                        if args.debug:
                            print("  -> Master row missing Author ID; cannot run ID search.")
                else:
                    if args.debug:
                        print(f"  -> Multiple cross-matches in master ({len(master_rows_hit)} rows); cannot disambiguate.")

                # Fall-through: still ambiguous
                writer.writerow({
                    "ScholarID": scholar_id,
                    "ClientFacultyId": client_fid,
                    "OrcId": input_orcid,
                    "Scopus Last Name": exp_surname,
                    "Scopus First Name": exp_given,
                    "Scopus ID": "",
                    "Scopus ORCiD": "",
                    "Status": "Ambiguous (Master)",
                })
                continue

            if args.debug:
                print("  -> No cross-match found in master, keeping as MORE THAN ONE.")
            writer.writerow({
                "ScholarID": scholar_id,
                "ClientFacultyId": client_fid,
                "OrcId": input_orcid,
                "Scopus Last Name": exp_surname,
                "Scopus First Name": exp_given,
                "Scopus ID": "",
                "Scopus ORCiD": "",
                "Status": "Ambiguous (Multi)",
            })

    print(f"\nWrote {len(df)} rows to {out_path}")

if __name__ == "__main__":
    main()
