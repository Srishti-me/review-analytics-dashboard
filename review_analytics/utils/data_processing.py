"""
Data Processing Module
Handles column mapping, cleaning, preprocessing, and derived field generation.
"""

import pandas as pd
import numpy as np
import re
import hashlib
from typing import Optional

# ─── Canonical Column Names ─────────────────────────────────────────────────────

CANONICAL_COLUMNS = {
    "review_text": ["review text", "review_text", "review", "text", "comment", "feedback", "user review", "user_review"],
    "star_rating": ["star rating", "star_rating", "rating", "stars", "score", "star"],
    "review_date": ["review date", "review_date", "date", "timestamp", "created_at", "created at", "time"],
    "app_version": ["app version", "app_version", "version", "app_ver", "build"],
    "reviewer_language": ["reviewer language", "reviewer_language", "language", "lang", "locale"],
    "device": ["device", "device_name", "device name", "model", "phone", "handset"],
    "cleaned_review_text": [
        "cleaned review text", "cleaned_review_text", "clean_text",
        "cleaned_text", "processed_text", "clean review", "cleaned review",
    ],
}

# ─── Noise Patterns ─────────────────────────────────────────────────────────────

NOISE_WORDS = {
    "ok", "okay", "fine", "nice", "good", "bad", "yes", "no", "hi", "hello",
    "hey", "thanks", "thank", "thx", "cool", "wow", "great", "best", "worst",
    "love", "hate", "super", "awesome", "terrible", "horrible", "excellent",
    "amazing", "fantastic", "perfect", "poor", "useless",
}

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
    "\U0000FE00-\U0000FE0F\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF]+",
    flags=re.UNICODE,
)


# ─── Column Mapping ─────────────────────────────────────────────────────────────

def auto_map_columns(uploaded_columns: list[str]) -> dict[str, Optional[str]]:
    """
    Attempt to automatically map uploaded column names to canonical names.
    Returns {canonical_name: uploaded_column_name or None}.
    """
    mapping = {}
    uploaded_lower = {col.strip().lower().replace("_", " "): col for col in uploaded_columns}

    for canonical, variants in CANONICAL_COLUMNS.items():
        matched = None
        for variant in variants:
            normalized = variant.strip().lower().replace("_", " ")
            if normalized in uploaded_lower:
                matched = uploaded_lower[normalized]
                break
        mapping[canonical] = matched

    return mapping


def validate_mapping(mapping: dict[str, Optional[str]]) -> tuple[bool, list[str]]:
    """Check if required columns are mapped. Returns (is_valid, missing_required)."""
    required = ["star_rating"]  # Minimum: we need at least ratings
    missing = [col for col in required if mapping.get(col) is None]
    return len(missing) == 0, missing


def apply_column_mapping(df: pd.DataFrame, mapping: dict[str, Optional[str]]) -> pd.DataFrame:
    """Rename columns based on mapping. Only rename columns that are mapped."""
    reverse_mapping = {v: k for k, v in mapping.items() if v is not None}
    df = df.rename(columns=reverse_mapping)
    return df


# ─── Preprocessing ───────────────────────────────────────────────────────────────

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full preprocessing pipeline:
    1. Date parsing
    2. Missing value handling
    3. Duplicate removal
    4. Type coercion
    5. Text cleaning
    6. Derived fields
    """
    df = df.copy()

    # ── Date Parsing ──
    if "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce", utc=True)
        df["review_date"] = df["review_date"].dt.tz_localize(None)
        df["review_date_only"] = df["review_date"].dt.date
        df["review_week"] = df["review_date"].dt.to_period("W").apply(
            lambda r: r.start_time if pd.notna(r) else pd.NaT
        )
        df["review_month"] = df["review_date"].dt.to_period("M").apply(
            lambda r: r.start_time if pd.notna(r) else pd.NaT
        )

    # ── Missing Values ──
    if "app_version" in df.columns:
        df["app_version"] = df["app_version"].fillna("Unknown")
    if "device" in df.columns:
        df["device"] = df["device"].fillna("Unknown")
    if "reviewer_language" in df.columns:
        df["reviewer_language"] = df["reviewer_language"].fillna("Unknown")

    # ── Star Rating Coercion ──
    if "star_rating" in df.columns:
        df["star_rating"] = pd.to_numeric(df["star_rating"], errors="coerce").fillna(0).astype(int)

    # ── Duplicate Removal ──
    subset_cols = [c for c in ["review_text", "star_rating", "review_date"] if c in df.columns]
    if subset_cols:
        before = len(df)
        df = df.drop_duplicates(subset=subset_cols, keep="first").reset_index(drop=True)

    # ── Text Cleaning ──
    if "cleaned_review_text" not in df.columns and "review_text" in df.columns:
        df["cleaned_review_text"] = df["review_text"].apply(_clean_text)
    elif "cleaned_review_text" in df.columns:
        df["cleaned_review_text"] = df["cleaned_review_text"].apply(
            lambda x: _clean_text(x) if pd.notna(x) else ""
        )

    # ── Derived Fields ──
    df = _add_derived_fields(df)

    return df


def _clean_text(text) -> str:
    """Basic text cleaning."""
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    return text


def _add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Add has_text_review and text_quality fields."""
    review_col = "cleaned_review_text" if "cleaned_review_text" in df.columns else "review_text"

    if review_col in df.columns:
        df["has_text_review"] = df[review_col].apply(
            lambda x: bool(x) and isinstance(x, str) and len(x.strip()) > 0
        )
        df["text_quality"] = df[review_col].apply(_classify_text_quality)
    else:
        df["has_text_review"] = False
        df["text_quality"] = "Empty"

    return df


def _classify_text_quality(text) -> str:
    """
    Classify text quality:
    - Empty: null / empty / whitespace
    - Noise: single chars, repeated chars, only emojis/punctuation, common noise words
    - Short: 1-2 meaningful words but too brief for LLM
    - Meaningful: 3+ words with actual content
    """
    if pd.isna(text) or not isinstance(text, str) or len(text.strip()) == 0:
        return "Empty"

    cleaned = text.strip()

    # Remove emojis for analysis
    text_no_emoji = EMOJI_PATTERN.sub("", cleaned).strip()

    # Only emojis / punctuation
    if len(text_no_emoji) == 0:
        return "Noise"

    # Only punctuation / special chars
    if re.match(r"^[^\w\s]+$", text_no_emoji):
        return "Noise"

    # Single character
    if len(text_no_emoji) <= 2:
        return "Noise"

    # Repeated characters (e.g., "aaaa", "!!!")
    if re.match(r"^(.)\1+$", text_no_emoji):
        return "Noise"

    # Count actual words
    words = [w for w in text_no_emoji.lower().split() if len(w) > 0]
    num_words = len(words)

    if num_words == 0:
        return "Noise"

    # Single noise word
    if num_words == 1:
        if words[0] in NOISE_WORDS or len(words[0]) <= 3:
            return "Noise"
        return "Short"

    # Two words — check if noise
    if num_words == 2:
        if all(w in NOISE_WORDS for w in words):
            return "Short"
        return "Short"

    # 3+ words — meaningful
    return "Meaningful"


# ─── Utility Functions ───────────────────────────────────────────────────────────

def get_review_hash(text: str) -> str:
    """Generate hash for review text for caching."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def get_processing_stats(df: pd.DataFrame) -> dict:
    """Return summary statistics about the processed dataset."""
    stats = {
        "total_reviews": len(df),
        "avg_rating": round(df["star_rating"].mean(), 2) if "star_rating" in df.columns else 0,
        "has_text_pct": round(df["has_text_review"].mean() * 100, 1) if "has_text_review" in df.columns else 0,
        "meaningful_count": len(df[df["text_quality"] == "Meaningful"]) if "text_quality" in df.columns else 0,
        "noise_count": len(df[df["text_quality"] == "Noise"]) if "text_quality" in df.columns else 0,
        "short_count": len(df[df["text_quality"] == "Short"]) if "text_quality" in df.columns else 0,
        "empty_count": len(df[df["text_quality"] == "Empty"]) if "text_quality" in df.columns else 0,
    }
    if "app_version" in df.columns:
        stats["unique_versions"] = df["app_version"].nunique()
    if "device" in df.columns:
        stats["unique_devices"] = df["device"].nunique()
    if "reviewer_language" in df.columns:
        stats["unique_languages"] = df["reviewer_language"].nunique()
    return stats
