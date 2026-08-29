"""AI assistant helper for relevance classification and duplicate detection.

This module provides conservative, local heuristics only — keyword-based relevance and
sequence-matcher duplicate merging. The OpenAI/embedding path has been removed.

Functions:
- filter_relevant_and_merge_duplicates(candidates, keywords, similarity_threshold=0.6, debug=False)

Candidates format: list of dicts with keys: 'title', 'desc', 'link', 'pub_date', 'category'
"""
from typing import List, Dict
import re
import unicodedata
import difflib


def _normalize_text(s: str) -> str:
    s = s or ''
    s = unicodedata.normalize('NFC', s)
    s = s.lower()
    s = re.sub(r"\s+", ' ', s).strip()
    return s


def _has_keyword(text: str, keywords: List[str]) -> bool:
    txt = _normalize_text(text)
    for k in keywords:
        if not k:
            continue
        if _normalize_text(k) in txt:
            return True
    return False


def _local_filter_relevance(candidates: List[Dict], keywords: List[str], debug: bool=False) -> List[Dict]:
    # Keep candidates that contain any of the keywords in title or description
    filtered = []
    for c in candidates:
        text = (c.get('title','') or '') + ' ' + (c.get('desc','') or '')
        if _has_keyword(text, keywords):
            filtered.append(c)
        else:
            if debug:
                print(f"FILTER: excluding as not matching keywords: {c.get('title')}")
    return filtered


def _local_merge_duplicates(candidates: List[Dict], threshold: float=0.6, debug: bool=False) -> List[Dict]:
    # Simple sequence matcher over title+desc
    keep = []
    skipped = [False]*len(candidates)
    texts = [ _normalize_text((c.get('title','') or '') + ' ' + (c.get('desc','') or '')) for c in candidates ]
    for i in range(len(candidates)):
        if skipped[i]:
            continue
        a = candidates[i]
        keep.append(a)
        for j in range(i+1, len(candidates)):
            if skipped[j]:
                continue
            ratio = difflib.SequenceMatcher(None, texts[i], texts[j]).ratio()
            if ratio >= threshold:
                skipped[j] = True
                if debug:
                    print(f"MERGE: merging duplicate: {candidates[j].get('title')} (ratio={ratio:.2f}) into {a.get('title')}")
    return keep


def filter_relevant_and_merge_duplicates(candidates: List[Dict], keywords: List[str], similarity_threshold: float=0.6, debug: bool=False) -> List[Dict]:
    """Filter out irrelevant articles and merge duplicates using local heuristics only."""
    if not candidates:
        return []
    # Relevance filter
    filtered = _local_filter_relevance(candidates, keywords, debug=debug)
    if not filtered:
        if debug:
            print('FILTER: no items matched keywords; returning original candidates')
        filtered = candidates
    # Merge duplicates using local sequence-matcher
    merged = _local_merge_duplicates(filtered, threshold=similarity_threshold, debug=debug)
    return merged
