"""AI assistant helper for relevance classification and duplicate detection.

This module provides a fallback local heuristic and an optional OpenAI-backed path
(if OPENAI_API_KEY is provided and openai package is installed).

Functions:
- filter_relevant_and_merge_duplicates(candidates, keywords, similarity_threshold=0.6, debug=False)

Candidates format: list of dicts with keys: 'title', 'desc', 'link', 'pub_date', 'category'
"""
from typing import List, Dict
import os
import re
import unicodedata
import difflib

try:
    import openai
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False


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
                print(f"AI_FALLBACK: excluding as not matching keywords: {c.get('title')}")
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
                    print(f"AI_FALLBACK: merging duplicate: {candidates[j].get('title')} (ratio={ratio:.2f}) into {a.get('title')}")
    return keep


def _openai_embeddings(texts: List[str], model: str = 'text-embedding-3-small'):
    # Returns list of embedding vectors or raises
    if not _HAS_OPENAI:
        raise RuntimeError('openai package not available')
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY not set')
    openai.api_key = key
    # batch in one call if small
    res = openai.Embedding.create(input=texts, model=model)
    embeddings = [r['embedding'] for r in res['data']]
    return embeddings


def _cosine(a, b):
    # assume lists
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a) ** 0.5
    nb = sum(x*x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na*nb)


def _ai_merge_with_embeddings(candidates: List[Dict], threshold: float=0.6, debug: bool=False) -> List[Dict]:
    texts = [ (c.get('title','') or '') + '\n' + (c.get('desc','') or '') for c in candidates ]
    try:
        embeddings = _openai_embeddings(texts)
    except Exception as e:
        if debug:
            print('AI_EMBED: failed, falling back to local merging:', e)
        return _local_merge_duplicates(candidates, threshold=threshold, debug=debug)

    keep = []
    skipped = [False]*len(candidates)
    for i in range(len(candidates)):
        if skipped[i]:
            continue
        a = candidates[i]
        keep.append(a)
        for j in range(i+1, len(candidates)):
            if skipped[j]:
                continue
            sim = _cosine(embeddings[i], embeddings[j])
            if sim >= threshold:
                skipped[j] = True
                if debug:
                    print(f"AI_EMBED: merging duplicate by embedding: {candidates[j].get('title')} (sim={sim:.3f}) into {a.get('title')}")
    return keep


def filter_relevant_and_merge_duplicates(candidates: List[Dict], keywords: List[str], similarity_threshold: float=0.6, debug: bool=False) -> List[Dict]:
    """Filter out irrelevant articles and merge duplicates.

    - If OpenAI API key is present and openai installed, embeddings merging will be used (better semantics).
    - Relevance is determined via keyword presence (fallback). This function is intentionally conservative.
    """
    if not candidates:
        return []
    # Relevance filter
    filtered = _local_filter_relevance(candidates, keywords, debug=debug)
    if not filtered:
        # if nothing matched, be conservative and return original candidates
        if debug:
            print('AI_FILTER: no items matched keywords; returning original candidates')
        filtered = candidates
    # Merge duplicates
    if _HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
        try:
            merged = _ai_merge_with_embeddings(filtered, threshold=similarity_threshold, debug=debug)
        except Exception as e:
            if debug:
                print('AI_FILTER: embedding merge failed, falling back to local:', e)
            merged = _local_merge_duplicates(filtered, threshold=similarity_threshold, debug=debug)
    else:
        merged = _local_merge_duplicates(filtered, threshold=similarity_threshold, debug=debug)

    return merged
