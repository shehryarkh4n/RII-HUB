# Research Identity Integration (RII) Toolkit

**Associated Paper:** "Connecting Digital Scholarly Researcher Identifiers & University Systems"
Shehryar Khan — Research Impact & Intelligence, University Libraries, Virginia Tech
*Presented at ASEE 2026*

This directory contains the core algorithmic implementations described in the paper's *Computational Framework* section. All three demos run in mock mode — **no API key is required**.

## Running the Demo

```bash
pip install -r requirements.txt
python main.py
```

## Core Capabilities

### 1. High-Throughput API Batching (`src/scopus_ops.py`)

Overcomes Scopus API rate limits by grouping hundreds of Author IDs into dynamic boolean queries:

```
AU-ID(10000000) OR AU-ID(10000001) OR ... OR AU-ID(10000024)
```

A batch size of 25–30 IDs reduces API call volume by ~96%.

### 2. Heuristic Institutional Matching (`src/institution_matcher.py`)

Aligns free-text affiliation strings to an official reference list using a three-stage waterfall:

1. **Aggressive normalization + exact match** — strips filler words, expands abbreviations
2. **Token-set match** — matches by word content regardless of order
3. **Validated fuzzy match** — Levenshtein distance with semantic guardrails (e.g., prevents "Law School" from matching "Med School")

**Usage:**

```python
from src.institution_matcher import InstitutionMatcher

# Replace with your institution's official name(s) and any internal IDs you use
official_list = {
    "1001": "Your Full Official Institution Name",
    "1002": "A Partner University Name",
}
matcher = InstitutionMatcher(official_list)

uid, method, score = matcher.match("Your Inst. Abbreviated")
# Returns: ("1001", "fuzzy_validated", 92)
```

The sample data in `main.py` uses Virginia Tech, UC Berkeley, and Texas A&M as concrete examples. Substitute any institutions from your own context.

### 3. Recursive Name Canonicalization (`src/utils.py`)

Generates comprehensive name variants to maximize recall when searching for researchers without verified identifiers:

```python
from src.utils import generate_name_variants

variants = generate_name_variants("Van der Waals", "Johannes Diderik")
# → "van der waals, johannes diderik"
# → "van der waals, j"
# → "van der waals, j."
# → "van der waals, jd"
# → "johannes diderik van der waals"
```

## Project Structure

```
sites/ASEE_CODE/
├── main.py                 # Runnable demo — showcases all three capabilities
├── requirements.txt        # Dependencies
└── src/
    ├── scopus_ops.py       # Batching engine
    ├── institution_matcher.py # Waterfall matching
    ├── ingestor.py         # Robust CSV/Excel ingestion
    └── utils.py            # Normalization + name variant generation
```

## Authors

**Shehryar Khan** — Research Impact & Intelligence
University Libraries, Virginia Tech
