import re
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from app.config import CHUNKS_FILE

_bm25_instance = None
_bm25_chunks = None


def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for legal text."""
    return re.findall(r"\b\w+\b", text.lower())


def get_bm25_store(chunks_path: Path = CHUNKS_FILE) -> Tuple[BM25Okapi, List[Dict[str, Any]]]:
    """Loads chunks and initializes the BM25 index."""
    global _bm25_instance, _bm25_chunks

    if _bm25_instance is not None and _bm25_chunks is not None:
        return _bm25_instance, _bm25_chunks

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    corpus = [tokenize(c.get("text", "")) for c in chunks]
    bm25 = BM25Okapi(corpus)

    _bm25_instance = bm25
    _bm25_chunks = chunks
    return bm25, chunks


def search_bm25(query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
    """
    Searches the BM25 index using exact keyword matching.
    Returns list of (chunk_dict, score) tuples.
    """
    bm25, chunks = get_bm25_store()
    tokenized_query = tokenize(query)
    scores = bm25.get_scores(tokenized_query)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append((chunks[idx], float(scores[idx])))
    return results
