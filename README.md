# RII-HUB: Research Identity Integration Toolkit

**Associated Paper:** "Connecting Digital Scholarly Researcher Identifiers & University Systems"
*Presented at ASEE 2026*

This repository provides the computational artifacts for the above paper, plus supporting tools used at Virginia Tech to automate the identification, validation, and disambiguation of Scopus Author IDs for engineering faculty.

---

## Repository Structure

```
RII-HUB/
├── sites/
│   ├── ASEE_CODE/                      # Primary paper artifact (mock demo, no API key needed)
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── scopus_ops.py           # High-throughput batching engine
│   │       ├── institution_matcher.py  # Heuristic institutional alignment
│   │       └── utils.py               # Name canonicalization & normalization
│   └── scopus/
│       └── author-search/
│           ├── single-author-tools/
│           │   └── single_author_search.py   # AUID identification workflow
│           └── basic-export/
│               ├── basic_export.py     # Publication export by author + date range
│               └── orcid_id.py        # ORCID export by Scopus Author ID
├── sample_inputs/                      # Synthetic example CSVs
├── requirements.txt                    # Root dependencies
└── .env.example                        # Environment variable template
```

---

## Quick Start

### Prerequisites

- Python 3.9–3.12
- An Elsevier Scopus API key (required for live API scripts; the ASEE demo runs without one)
- Internet access for API calls

### Installation

```bash
git clone https://github.com/shehryarkh4n/RII-HUB
cd RII-HUB

python3 -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# then edit .env
```

---

## Part 1 — ASEE Paper Demo (No API Key Required)

The `sites/ASEE_CODE/` directory is the primary artifact for the paper. It demonstrates all three algorithmic contributions with mock data and requires no API key.

```bash
cd sites/ASEE_CODE
pip install -r requirements.txt   # if not already done from root
python main.py
```

### What it demonstrates

#### 1. High-Throughput API Batching (`src/scopus_ops.py`)

Overcomes Scopus API rate limits by constructing dynamic boolean queries:

```
AU-ID(10000000) OR AU-ID(10000001) OR ... OR AU-ID(10000024)
```

Batching 25–30 IDs per query reduces API call volume by ~96%.

#### 2. Heuristic Institutional Matching (`src/institution_matcher.py`)

Aligns free-text institution names to an official reference list using a three-stage waterfall:

| Stage | Method | Example match |
|-------|--------|---------------|
| 1 | Exact normalized | `"virginia polytechnic inst"` → VT |
| 2 | Token-set (order-independent) | `"Institute State Virginia Polytechnic"` → VT |
| 3 | Validated fuzzy (Levenshtein) | `"Va. Poly. Inst."` → VT |

**Adapting for your institution:** Pass your own reference dictionary:

```python
from src.institution_matcher import InstitutionMatcher

official_list = {
    "1001": "Your Full Official Institution Name",
    "1002": "Partner University Name",
}
matcher = InstitutionMatcher(official_list)
uid, method, score = matcher.match("Your Inst. Abbreviated Name")
```

Virginia Tech appears in the sample data as an illustrative example. Substitute any institution.

#### 3. Recursive Name Canonicalization (`src/utils.py`)

Generates name variants to maximize recall when searching without verified identifiers:

```python
from src.utils import generate_name_variants
variants = generate_name_variants("Van der Waals", "Johannes Diderik")
# → {"van der waals, johannes diderik", "van der waals, j", "johannes diderik van der waals", ...}
```

---

## Part 2 — Scopus Author ID Identification (`single_author_search.py`)

Maps a faculty roster to verified Scopus Author IDs using the multi-stage disambiguation logic described in the paper.

**Requires:** Elsevier API key in `.env`.

```bash
python sites/scopus/author-search/single-author-tools/single_author_search.py \
  --in sample_inputs/faculty_roster.csv \
  --ref sample_inputs/master_list.csv \
  --affil "(AFFIL(Virginia Tech) OR AFFIL(Virginia Polytechnic))"
```

### Adapting for your institution

Replace the `--affil` value with your institution's Scopus affiliation string. Use the Scopus search interface to find how your institution appears:

```bash
# MIT example
--affil "(AFFIL(MIT) OR AFFIL(Massachusetts Institute of Technology))"

# Large state system example
--affil "(AFFIL(University of Michigan) OR AFFIL(U Michigan))"
```

The default is set to Virginia Tech's two registered Scopus affiliation names as a concrete example.

### Input files

**`sample_inputs/faculty_roster.csv`** — one row per faculty member:

```csv
scholarname,scholarid,clientfacultyid,orcid
"DOE, JANE",S001,F101,0000-0002-1234-5678
"SMITH, ROBERT A",S002,F102,
```

- `scholarname`: `"SURNAME, GIVEN"` format (Academic Analytics export convention; adapt `parse_name_column` in `utils.py` if your source uses a different format)
- `scholarid`, `clientfacultyid`: your internal IDs (passed through to output)
- `orcid`: optional; passed through

**`sample_inputs/master_list.csv`** — a known-good reference list of author names and Scopus IDs (e.g., from SciVal or a prior validated run):

```csv
Author Full Name,Author ID
Doe, Jane,55432100800
```

### Output columns

| Column | Description |
|--------|-------------|
| `ScholarID` | Your internal ID (from input) |
| `ClientFacultyId` | Your internal ID (from input) |
| `OrcId` | ORCID from input |
| `Scopus Last Name` | Surname returned by Scopus |
| `Scopus First Name` | Given name returned by Scopus |
| `Scopus ID` | Verified Scopus Author ID |
| `Scopus ORCiD` | ORCID returned by Scopus |
| `Status` | Match method (see below) |

**Status values:**

| Status | Meaning |
|--------|---------|
| `Match (Direct)` | Single Scopus result; unambiguous |
| `Match (Master)` | Cross-validated against reference list |
| `Match (ID)` | Confirmed via direct AU-ID lookup |
| `No Match` | No Scopus result found |
| `No Match (ID)` | AU-ID lookup returned empty |
| `Ambiguous (Multi)` | Multiple results, could not disambiguate |
| `Ambiguous (Master)` | Multiple master-list hits |
| `Ambiguous (ID)` | Multiple results from AU-ID lookup |

---

## Part 3 — Publication & ORCID Export

### Publication export

Exports bibliographic records for a list of Scopus Author IDs over a date range.

**Requires:** API key.

```bash
python sites/scopus/author-search/basic-export/basic_export.py \
  --in sample_inputs/author_export.csv \
  --subfolder my_export
```

Input CSV format (`sample_inputs/author_export.csv`):

```csv
author_id,start_date,end_date
55432100800,2019-01-01,2024-12-31
```

Output columns: `Authors`, `Author full names`, `Author(s) ID`, `Title`, `Year`, `Source title`, `Cited by`, `DOI`, `Affiliations`, `Author Keywords`, `Document Type`, `Source`, `EID`

Results write to `local_outputs/<subfolder>/` (created automatically).

### ORCID export

Retrieves the ORCID iD on file in Scopus for each Author ID.

```bash
python sites/scopus/author-search/basic-export/orcid_id.py \
  --in sample_inputs/orcid_lookup.csv
```

Input CSV: single column `author_id`.

---

## Configuration Reference

All scripts load `.env` automatically via `python-dotenv`. See `.env.example` for the full template.

| Variable | Required | Description |
|----------|----------|-------------|
| `ELSEVIER_API_KEY` | Yes (API scripts) | Your Elsevier Scopus API key |
| `AUTHOR_DELIM` | No | Delimiter for multi-author fields (default: `"; "`) |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` | Activate venv and run `pip install -r requirements.txt` |
| `401 Unauthorized` | Check `.env` has a valid `ELSEVIER_API_KEY` |
| Empty results | Widen date range; verify author has publications in that window |
| SSL / network errors | Check firewall/VPN; scripts need outbound HTTPS to `api.elsevier.com` |

---

## Repo Author

**Shehryar Khan** - shehryarkhan@vt.edu

Research Impact & Intelligence
University Libraries, Virginia Tech
