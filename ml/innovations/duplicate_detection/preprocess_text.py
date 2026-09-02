"""
Duplicate Detection — Text Preprocessing.

Cleans and normalizes work_description text for the eligible pool
(after Stage 1 & 2 filtering) before generating embeddings.
"""
import re
import pandas as pd


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize work_description text for eligible records only.

    Adds column:
    - description_clean: Preprocessed text ready for embedding

    Only processes rows where filter_status == 'eligible'.
    """
    df = df.copy()
    df["description_clean"] = ""

    eligible_mask = df["filter_status"] == "eligible"
    eligible_texts = df.loc[eligible_mask, "work_description"].copy()

    print(f"[Preprocess] Cleaning {eligible_texts.shape[0]} eligible descriptions...")

    cleaned = eligible_texts.apply(_clean_text)
    df.loc[eligible_mask, "description_clean"] = cleaned

    # Drop any that became empty after cleaning
    empty_after = eligible_mask & (df["description_clean"].str.strip() == "")
    if empty_after.any():
        df.loc[empty_after, "filter_status"] = "excluded_empty_after_clean"
        df.loc[empty_after, "filter_reason"] = "Description became empty after text cleaning."
        print(f"  {empty_after.sum()} descriptions became empty after cleaning — excluded")

    final_eligible = (df["filter_status"] == "eligible").sum()
    print(f"[Preprocess] Done. {final_eligible} descriptions ready for embedding.")

    return df


def _clean_text(text: str) -> str:
    """
    Clean a single work_description string.

    Steps:
    1. Lowercase
    2. Normalize whitespace (collapse multiple spaces, strip)
    3. Remove special characters but keep alphanumeric, spaces, common punctuation
    4. Remove numeric-only tokens (ward numbers, plot numbers etc.)
       that don't carry semantic meaning for similarity
    5. Strip very short results (< 10 chars) — likely not useful
    """
    if pd.isna(text):
        return ""

    t = str(text).lower().strip()

    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t)

    # Remove characters that are not alphanumeric, space, or basic punctuation
    t = re.sub(r'[^a-z0-9\s,.\-/()]', ' ', t)

    # Collapse repeated whitespace again
    t = re.sub(r'\s+', ' ', t).strip()

    # Remove standalone numbers (ward 15, plot 817/3, pry no 1/a)
    # Keep numbers attached to words (e.g., "phase2")
    t = re.sub(r'\b\d+[/\-]?\d*[/\-]?\d*\b', '', t)
    t = re.sub(r'\s+', ' ', t).strip()

    return t
