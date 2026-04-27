import re
from typing import Set, Iterable

def normalize_text_aggressive(text: str) -> str:
    """
    Aggressively normalizes text for exact matching.
    - Lowercases
    - Removes all punctuation
    - Removes common filler words (the, of, at, etc.)
    - Standardizes common abbreviations (univ -> university)
    """
    if not text:
        return ""
    
    t = text.strip().lower()
    
    # Standardize variations
    t = re.sub(r"\ba\s*&\s*m\b", "am", t)
    
    # Remove punctuation
    t = re.sub(r"[^\w\s]", " ", t)
    
    # Standardize academic terms
    replacements = {
        "univ": "university",
        "coll": "college",
        "inst": "institute",
        "dept": "department",
        "lab": "laboratory"
    }
    
    tokens = t.split()
    tokens = [replacements.get(tok, tok) for tok in tokens]
    
    # Remove filler words
    filler_words = {"the", "of", "at", "in", "and", "a", "an", "for", "to", "on", "system", "campus"}
    tokens = [tok for tok in tokens if tok not in filler_words]
    
    return " ".join(tokens)

def normalize_text_moderate(text: str) -> str:
    """
    Moderately normalizes text for fuzzy matching.
    - Keeps structure mostly intact but cleans punctuation and spacing.
    """
    if not text:
        return ""
    
    t = text.strip().lower()
    t = t.replace("&", "and")
    t = re.sub(r"[.,\(\)\-_/]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    
    return t

def generate_name_variants(surname: str, given: str) -> Iterable[str]:
    """
    Generates common variations of a researcher's name for matching.
    e.g., "Doe, John" -> ["doe, john", "doe, j", "doe, j.", "j doe", ...]
    """
    s = (surname or "").strip().lower()
    g = (given or "").strip().lower()
    
    if not s:
        return []

    variants = set()
    
    # Full: surname, given
    if g:
        variants.add(f"{s}, {g}")
        variants.add(f"{g} {s}")
        
        # Initial: surname, j
        initial = g[0]
        variants.add(f"{s}, {initial}")
        variants.add(f"{s}, {initial}.")
        variants.add(f"{initial} {s}")
        
        # Initials from multi-word given name
        full_initials = "".join(t[0] for t in re.split(r"[\s\-]+", g) if t)
        if len(full_initials) > 1:
             variants.add(f"{s}, {full_initials}")
    
    # Just surname (risky, but sometimes useful in strict contexts)
    # variants.add(s) 
    
    return variants
