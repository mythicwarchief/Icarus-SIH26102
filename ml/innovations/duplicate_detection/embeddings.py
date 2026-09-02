"""
Duplicate Detection — Embedding Generation.

Generates sentence embeddings for eligible work_description texts
using sentence-transformers (all-MiniLM-L6-v2).

The embeddings are computed in batches and stored alongside the
DataFrame for downstream similarity computation.
"""
import os
import numpy as np
import pandas as pd

# Model name — same lightweight model, good balance of speed and quality
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 256


def generate_embeddings(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Generate sentence embeddings for all eligible (cleaned) descriptions.

    Args:
        df: DataFrame with 'description_clean' and 'filter_status' columns.

    Returns:
        Tuple of (df, embeddings_array) where embeddings_array has shape
        (n_eligible, embedding_dim) and is aligned with the eligible rows.
    """
    from sentence_transformers import SentenceTransformer

    eligible_mask = df["filter_status"] == "eligible"
    texts = df.loc[eligible_mask, "description_clean"].tolist()
    n = len(texts)

    if n == 0:
        print("[Embeddings] No eligible texts to embed.")
        return df, np.array([])

    print(f"[Embeddings] Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"[Embeddings] Encoding {n} descriptions (batch_size={BATCH_SIZE})...")
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        normalize_embeddings=True,  # L2-normalized for cosine similarity via dot product
    )

    print(f"[Embeddings] Done. Shape: {embeddings.shape}")
    return df, embeddings
