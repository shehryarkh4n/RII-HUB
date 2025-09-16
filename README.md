# RII-HUB

Tools, scripts & information for internal team usage

## Table of Contents

* [Overview](#overview)
* [Prerequisites](#prerequisites)
* [Quick Start (Recommended)](#quick-start-recommended)
* [Configuration](#configuration)
* [Scopus](#scopus)

  * [Author Search](#author-search)
  * [Input CSV Format](#input-csv-format)
  * [Output Columns](#output-columns)
  * [Examples](#examples)
* [Troubleshooting](#troubleshooting)

---

## Overview

This repo provides internal tools and scripts for Elsevier/Scopus workflows. The main entry point today is the **Scopus Author Search** CSV export.

## Prerequisites

* **Python**: 3.9–3.12
* **Elsevier API Key** (required)
* **Git** (to clone the repo)
* Internet access (for API calls)
* VT VPN is off-campus

---

## Quick Start (Recommended)

> These steps create a virtual environment, install dependencies, and run the script.

1. **Clone and enter the repo**

```bash
git clone https://github.com/shehryarkh4n/RII-HUB RII-HUB
cd RII-HUB
```

2. **Create & activate a virtual environment**

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
```

3. **Install dependencies**

**Using `requirements.txt`**

Run the following command to process all packages required:

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

At the repo root, create a file named `.env` with the following defaults:

```
ELSEVIER_API_KEY=YOUR_REAL_KEY

# Optional: delimiter when combining author names (default shown)
AUTHOR_DELIM="; "
```

---

## Configuration

* **`.env`** is loaded automatically by the scripts (via `python-dotenv`).
* Required:

  * `ELSEVIER_API_KEY` — your Elsevier API key.
* Optional:

  * `AUTHOR_DELIM` — how author names are joined in outputs (default: `"; "`).

---

## Scopus

### Author Search

Generates a CSV with bibliographic fields for one or more authors over a date range.

**Command**

```bash
python sites/scopus/author-search/basic-export/basic_export.py --in <INPUT_CSV> --out <OUTPUT_CSV> [--debug]

OR

python sites/scopus/author-search/basic-export/basic_export.py --in <INPUT_CSV> --subfolder <folder name> [--debug]
```

Note here that the script will auto-create a folder called `local_outputs`. To create a subfolder for organization, pass in the `--subfolder` clause, followed by a name. To pass a direct path and a name for the output file, use `--out` instead. Examples for both are given below.

### Input CSV Format

* File must be CSV with header:

```csv
author_id,start_date,end_date
54403605200,2019-01-01,2021-12-01
# more rows...
```

* `author_id`: Scopus Author ID (numeric)
* `start_date` / `end_date`: `YYYY-MM-DD`

### Output Columns

The export produces these columns:

* `Authors`
* `Author full names`
* `Author(s) ID`
* `Title`
* `Year`
* `Source title`
* `Cited by`
* `DOI`
* `Affiliations`
* `Author Keywords`
* `Document Type`
* `Source`
* `EID`

> By default, outputs are saved under a `local_outputs/` folder at the repo root (created automatically if missing). Site-specific subfolders may be created.

### Examples

**Minimal run**

```bash
python sites/scopus/author-search/basic-export/basic_export.py \
  --in INPUT_SciVal.csv \
  --subfolder scopus

OR

python sites/scopus/author-search/basic-export/basic_export.py \
  --in INPUT_SciVal.csv \
  --out path/to/some/folder/fileName.csv
```

**An example with debug logging**

```bash
python sites/scopus/author-search/basic-export/basic_export.py \
  --in INPUT_SciVal.csv \
  --subfolder scopus \
  --debug
```

---

## Troubleshooting

* **`ModuleNotFoundError`**
  Ensure your venv is active and dependencies are installed:

  ```bash
  source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
  pip install -r requirements.txt
  ```
* **Missing API key / 401 errors**
  Confirm `.env` exists at repo root and contains a valid `ELSEVIER_API_KEY`.
* **SSL or network errors**
  Check firewall/VPN settings; the script needs outbound HTTPS to Elsevier APIs.
* **Dates produce empty results**
  Verify the author has publications in the given window; try widening the range.
