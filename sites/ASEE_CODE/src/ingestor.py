import pandas as pd
from pathlib import Path
from typing import Optional, Tuple

ENCODINGS = ["utf-8", "latin-1", "cp1252", "iso-8859-1"]

def safe_read_csv(file_path: str) -> Optional[pd.DataFrame]:
    """
    Attempts to read a CSV with multiple encodings.
    """
    for enc in ENCODINGS:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    return None

def extract_metadata_from_filename(filename: str) -> str:
    """
    Heuristic extraction of author names from filenames.
    Format: 'lastname_firstname_institution.csv' -> 'Lastname Firstname'
    """
    stem = Path(filename).stem
    parts = stem.split('_')
    
    if len(parts) >= 2:
        return f"{parts[0].title()} {parts[1].title()}"
    return stem.replace('_', ' ').title()

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes empty columns and sanitizes headers.
    """
    # Standardize headers
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    
    # Drop empty cols
    df = df.dropna(axis=1, how='all')
    
    return df
