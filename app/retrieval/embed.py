import time
import numpy as np
from typing import List, Union
from huggingface_hub import InferenceClient
from app.config import HUGGINGFACEHUB_API_TOKEN

# Free, fast, lightweight model supported on HF Serverless Inference API
DEFAULT_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_hf_client() -> InferenceClient:
    """Returns an authenticated Hugging Face InferenceClient."""
    return InferenceClient(api_key=HUGGINGFACEHUB_API_TOKEN)


def embed_text(text: str, client: InferenceClient = None, model: str = DEFAULT_HF_MODEL) -> np.ndarray:
    """
    Embeds a single string using Hugging Face Inference API.
    Returns normalized 1D numpy array of shape (384,).
    """
    if not HUGGINGFACEHUB_API_TOKEN:
        raise ValueError("No Hugging Face token provided; using BM25 fallback.")

    if client is None:
        client = get_hf_client()

    clean_text = text.strip() or "empty"
    vector = client.feature_extraction(clean_text, model=model)
    arr = np.array(vector, dtype=np.float32)

    # Flatten if nested
    if arr.ndim > 1:
        arr = arr.flatten()[:EMBEDDING_DIM]

    # Normalize for cosine similarity via inner product
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr


def embed_batch(
    texts: List[str],
    batch_size: int = 32,
    client: InferenceClient = None,
    model: str = DEFAULT_HF_MODEL,
) -> np.ndarray:
    """
    Embeds a list of texts in batches using the Hugging Face Inference API.
    Returns a 2D numpy array of shape (N, 384).
    """
    if client is None:
        client = get_hf_client()

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = [t.strip() or "empty" for t in texts[i : i + batch_size]]
        retries = 3
        while retries > 0:
            try:
                vectors = client.feature_extraction(batch, model=model)
                arr = np.array(vectors, dtype=np.float32)
                # Ensure 2D shape (batch_len, EMBEDDING_DIM)
                if arr.ndim == 1:
                    arr = arr.reshape(1, -1)
                elif arr.ndim == 3:
                    # In case of token embeddings (batch, seq_len, dim), mean-pool
                    arr = np.mean(arr, axis=1)

                all_embeddings.append(arr)
                break
            except Exception as e:
                retries -= 1
                if retries == 0:
                    print(f"Failed to embed batch {i} to {i+len(batch)}: {e}")
                    # Fallback with zero-vectors if permanent error
                    all_embeddings.append(np.zeros((len(batch), EMBEDDING_DIM), dtype=np.float32))
                else:
                    time.sleep(1.5)

    result = np.vstack(all_embeddings)
    # Normalize rows
    norms = np.linalg.norm(result, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return result / norms
