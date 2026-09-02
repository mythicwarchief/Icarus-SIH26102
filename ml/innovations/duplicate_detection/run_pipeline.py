"""
Duplicate Detection Pipeline — Main Runner.

Runs the complete duplicate/similar project detection pipeline:
  Stage 1: Exact-match / boilerplate filter
  Stage 2: Beneficiary-style text filter
  Stage 3: Text preprocessing
  Stage 4: Embedding generation (sentence-transformers)
  Stage 5: Within-constituency similarity scoring
  Stage 6: Save outputs

Usage:
    python -m ml.duplicate_detection.run_pipeline
"""
import os
import sys
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ml.duplicate_detection.filters import load_descriptions, run_filters
from ml.duplicate_detection.preprocess_text import preprocess
from ml.duplicate_detection.embeddings import generate_embeddings
from ml.duplicate_detection.similarity import find_similar_pairs, save_outputs


def run_pipeline():
    """Execute the full duplicate detection pipeline."""
    start_time = time.time()
    print("=" * 70)
    print("  MPLADS DUPLICATE / SIMILAR PROJECT DETECTION PIPELINE")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Stage 1 & 2: Load descriptions and apply filters
    print("\n[1/5] Loading descriptions and applying filters...")
    print("-" * 50)
    df = load_descriptions()
    df = run_filters(df)

    # Stage 3: Text preprocessing
    print("\n[2/5] Preprocessing eligible text...")
    print("-" * 50)
    df = preprocess(df)

    # Stage 4: Generate embeddings
    print("\n[3/5] Generating embeddings...")
    print("-" * 50)
    df, embeddings = generate_embeddings(df)

    # Stage 5: Find similar pairs
    print("\n[4/5] Finding similar pairs within constituencies...")
    print("-" * 50)
    pairs_df, df = find_similar_pairs(df, embeddings)

    # Stage 6: Save outputs
    print("\n[5/5] Saving outputs...")
    print("-" * 50)
    save_outputs(pairs_df, df)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  DUPLICATE DETECTION PIPELINE COMPLETE in {elapsed:.1f} seconds")
    print("=" * 70)

    return pairs_df, df


if __name__ == "__main__":
    run_pipeline()
