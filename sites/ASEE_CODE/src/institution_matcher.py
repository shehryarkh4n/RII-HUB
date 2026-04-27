from collections import defaultdict
from typing import List, Tuple, Dict, Optional
try:
    from rapidfuzz import process, fuzz
except ImportError:
    print("Warning: rapidfuzz not installed. Fuzzy matching will be disabled.")
    process = None

from .utils import normalize_text_aggressive, normalize_text_moderate

class InstitutionMatcher:
    """
    Aligns institutional names from disparate sources (e.g., IPEDS, Scival, HR Data).
    Uses a waterfall approach: Exact -> Token Set -> Heuristic Fuzzy.
    """

    def __init__(self, reference_institutions: Dict[str, str]):
        """
        Args:
            reference_institutions: Dict mapping {Unique_ID: "Official Name"}
        """
        self.ref_data = reference_institutions
        self._build_indexes()

    def _build_indexes(self):
        """Pre-computes normalized lookups for speed."""
        self.exact_index = {}
        self.token_index = {}
        self.fuzzy_pool = []

        for uid, name in self.ref_data.items():
            # Exact index
            norm = normalize_text_aggressive(name)
            if norm:
                self.exact_index[norm] = uid
            
            # Token index (frozenset for order-independence)
            tokens = frozenset(norm.split())
            if tokens:
                self.token_index[tokens] = uid

            # Fuzzy pool (keep moderate normalization)
            self.fuzzy_pool.append((uid, name, normalize_text_moderate(name)))

    def match(self, name: str) -> Tuple[Optional[str], str, int]:
        """
        Attempts to match an input name to the reference list.
        Returns: (Matched_UID, Match_Method, Confidence_Score)
        """
        if not name:
            return None, "empty", 0

        # 1. Exact Match
        norm = normalize_text_aggressive(name)
        if norm in self.exact_index:
            return self.exact_index[norm], "exact_normalized", 100

        # 2. Token Set Match
        tokens = frozenset(norm.split())
        if tokens in self.token_index:
            return self.token_index[tokens], "token_set_exact", 99

        # 3. Fuzzy Match (if rapidfuzz available)
        if process:
            mod_norm = normalize_text_moderate(name)
            
            # Extract top candidate
            # pool elements are (uid, original, normalized)
            # process.extract returns list of (match, score, index)
            candidates = process.extract(
                mod_norm, 
                [x[2] for x in self.fuzzy_pool], 
                scorer=fuzz.token_set_ratio, 
                limit=1
            )
            
            if candidates:
                match_str, score, idx = candidates[0]
                uid = self.fuzzy_pool[idx][0]
                target_name = self.fuzzy_pool[idx][1]

                if self._validate_fuzzy_match(name, target_name, score):
                    return uid, "fuzzy_validated", int(score)
        
        return None, "no_match", 0

    def _validate_fuzzy_match(self, source: str, target: str, score: float) -> bool:
        """
        Heuristic validation to prevent false positives (e.g., 'X State' vs 'X Tech').
        """
        if score < 85:
            return False
        if score >= 95:
            return True

        # Custom validation logic
        s_norm = normalize_text_moderate(source)
        t_norm = normalize_text_moderate(target)
        
        # Check for conflicting "distinctive types"
        # e.g., don't match "Medical College" with "Law School" even if other words match
        types = {"medical", "law", "business", "technical", "community"}
        s_types = set(s_norm.split()) & types
        t_types = set(t_norm.split()) & types
        
        if s_types and t_types and s_types != t_types:
            return False

        return True
