from typing import List, Dict, Any
from app.retrieval.vector_store import search_vector_store
from app.retrieval.bm25_store import search_bm25


def hybrid_retrieve(query: str, top_k: int = 5, rrf_k: int = 60) -> List[Dict[str, Any]]:
    """
    Combines FAISS dense vector search and BM25 keyword search
    using Reciprocal Rank Fusion (RRF).
    """
    dense_results = []
    try:
        dense_results = search_vector_store(query, top_k=top_k * 2)
    except Exception as e:
        print(f"Warning: Dense vector search encountered error ({e}). Proceeding with BM25 lexical search.")

    bm25_results = search_bm25(query, top_k=top_k * 2)

    chunk_scores: Dict[int, float] = {}
    chunk_map: Dict[int, Dict[str, Any]] = {}

    # RRF for dense results
    for rank, (chunk, _) in enumerate(dense_results):
        cid = chunk["chunk_id"]
        chunk_map[cid] = chunk
        chunk_scores[cid] = chunk_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

    # RRF for BM25 results
    for rank, (chunk, _) in enumerate(bm25_results):
        cid = chunk["chunk_id"]
        chunk_map[cid] = chunk
        chunk_scores[cid] = chunk_scores.get(cid, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Sort chunks by fused score
    sorted_cids = sorted(chunk_scores.keys(), key=lambda cid: chunk_scores[cid], reverse=True)

    results = []
    for cid in sorted_cids[:top_k]:
        chunk = dict(chunk_map[cid])
        chunk["retrieval_score"] = round(chunk_scores[cid], 5)
        results.append(chunk)

    return results
