import json
import os
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.config import DATA_DIR, CHUNKS_FILE
from app.retrieval.embed import embed_batch, embed_text, EMBEDDING_DIM

FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
CHUNKS_CACHE_PATH = DATA_DIR / "indexed_chunks.json"

_cached_index = None
_cached_chunks = None


def build_and_save_index(chunks_path: Path = CHUNKS_FILE, index_path: Path = FAISS_INDEX_PATH) -> faiss.IndexFlatIP:
    """
    Reads chunks.json, generates embeddings via Hugging Face API,
    builds a FAISS inner-product index, and saves it to disk.
    """
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"Chunks file not found at {chunks_path}")

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"Building vector index for {len(chunks)} chunks...")
    texts = [c.get("text", "") for c in chunks]

    embeddings = embed_batch(texts, batch_size=64)

    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))

    # Save cached chunks reference
    with open(CHUNKS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False)

    print(f"FAISS index successfully saved to {index_path} ({index.ntotal} vectors).")
    return index


def get_vector_store() -> Tuple[faiss.IndexFlatIP, List[Dict[str, Any]]]:
    """Loads or builds the FAISS index and chunk metadata."""
    global _cached_index, _cached_chunks

    if _cached_index is not None and _cached_chunks is not None:
        return _cached_index, _cached_chunks

    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(CHUNKS_FILE):
        try:
            # Check file size to ensure it's a real binary index (> 10KB) and not an unresolved LFS pointer
            if os.path.getsize(FAISS_INDEX_PATH) > 10000:
                print("Loading existing FAISS index from disk...")
                index = faiss.read_index(str(FAISS_INDEX_PATH))
                with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
                _cached_index = index
                _cached_chunks = chunks
                return index, chunks
            else:
                print("FAISS index file is too small (likely unresolved LFS pointer). Rebuilding index...")
        except Exception as e:
            print(f"Warning: Failed to load FAISS index from disk ({e}). Rebuilding...")

    index = build_and_save_index()
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    _cached_index = index
    _cached_chunks = chunks
    return index, chunks


def search_vector_store(query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
    """
    Embeds a search query and queries FAISS for the top_k most similar chunks.
    Returns list of (chunk_dict, score) tuples.
    """
    index, chunks = get_vector_store()
    q_vec = embed_text(query).reshape(1, -1)
    scores, indices = index.search(q_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(chunks):
            results.append((chunks[idx], float(score)))
    return results
