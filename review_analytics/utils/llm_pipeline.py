"""
LLM Pipeline Module
Handles OpenAI-based review enrichment with batching, caching, and progress tracking.
"""

import json
import time
import hashlib
import streamlit as st
import pandas as pd
from openai import OpenAI

# DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_MODEL = "llama-3.1-8b-instant"
BATCH_SIZE = 10
MAX_RETRIES = 3
RETRY_DELAY = 2

LLM_COLUMNS = [
    "review_type", "sentiment", "topic", "subtopic",
    "affected_area", "severity", "actionability", "summary",
]

SYSTEM_PROMPT = """You are an expert app review analyst. Categorize mobile app reviews into structured fields.

For each review, return a JSON object with:
1. review_type: "Complaint"|"Praise"|"Feature Request"|"Question / Confusion"|"Noise / Irrelevant"
2. sentiment: "Positive"|"Neutral"|"Negative"
3. topic: "App Stability"|"Login / OTP"|"Payments / UPI"|"Recharge"|"Account Access"|"Customer Support"|"Performance"|"Trust / Fraud Concern"|"User Experience"|"Positive Feedback"|"Other"
4. subtopic: specific subtopic string
5. affected_area: "Login"|"UPI"|"Recharge"|"Account"|"Support"|"Performance"|"Security"|"General App"
6. severity: "High"(blocked/crash/failed payment)|"Medium"(broken flow/support issue)|"Low"(minor/suggestion)
7. actionability: "Actionable"|"Not Actionable"
8. summary: one-line summary (max 15 words)

Return {"reviews": [...]} JSON with one object per review in input order. Do NOT speculate about root causes or fixes."""


# def get_openai_client(api_key: str) -> OpenAI:
#     return OpenAI(api_key=api_key)

def get_openai_client(api_key: str) -> OpenAI:
    # Using Groq API as default, as requested.
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def _build_batch_prompt(reviews: list[dict]) -> str:
    lines = []
    for i, r in enumerate(reviews):
        rating = r.get("star_rating", "N/A")
        text = r.get("cleaned_review_text", r.get("review_text", ""))
        lines.append(f"Review {i+1} (Rating: {rating}★): {text}")
    return "\n".join(lines)


def _get_default_llm_fields(rating: int = 3) -> dict:
    if rating >= 4:
        return {"review_type": "Praise", "sentiment": "Positive", "topic": "Positive Feedback",
                "subtopic": "General satisfaction", "affected_area": "General App",
                "severity": "Low", "actionability": "Not Actionable", "summary": "Positive review"}
    elif rating <= 2:
        return {"review_type": "Complaint", "sentiment": "Negative", "topic": "Other",
                "subtopic": "Unspecified issue", "affected_area": "General App",
                "severity": "Medium", "actionability": "Actionable", "summary": "Negative review without details"}
    return {"review_type": "Noise / Irrelevant", "sentiment": "Neutral", "topic": "Other",
            "subtopic": "N/A", "affected_area": "General App",
            "severity": "Low", "actionability": "Not Actionable", "summary": "Neutral review"}


def _validate_result(result: dict) -> dict:
    valid = {}
    valid_types = {"Complaint", "Praise", "Feature Request", "Question / Confusion", "Noise / Irrelevant"}
    valid["review_type"] = result.get("review_type", "Noise / Irrelevant")
    if valid["review_type"] not in valid_types:
        valid["review_type"] = "Noise / Irrelevant"

    valid_sentiments = {"Positive", "Neutral", "Negative"}
    valid["sentiment"] = result.get("sentiment", "Neutral")
    if valid["sentiment"] not in valid_sentiments:
        valid["sentiment"] = "Neutral"

    valid["topic"] = result.get("topic", "Other") or "Other"
    valid["subtopic"] = result.get("subtopic", "N/A") or "N/A"
    valid["affected_area"] = result.get("affected_area", "General App") or "General App"

    valid_sev = {"High", "Medium", "Low"}
    valid["severity"] = result.get("severity", "Low")
    if valid["severity"] not in valid_sev:
        valid["severity"] = "Low"

    valid_act = {"Actionable", "Not Actionable"}
    valid["actionability"] = result.get("actionability", "Not Actionable")
    if valid["actionability"] not in valid_act:
        valid["actionability"] = "Not Actionable"

    valid["summary"] = result.get("summary", "No summary") or "No summary"
    return valid


def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode("utf-8")).hexdigest()


def _call_llm_with_retry(client, model, batch_reviews):
    prompt = _build_batch_prompt(batch_reviews)
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=4096,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        return v
                return [parsed]
            return parsed if isinstance(parsed, list) else [parsed]
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                st.warning(f"LLM call failed: {e}")
                return [_get_default_llm_fields() for _ in batch_reviews]
    return [_get_default_llm_fields() for _ in batch_reviews]


def process_reviews_with_llm(df, api_key, model=DEFAULT_MODEL, batch_size=BATCH_SIZE, progress_callback=None):
    df = df.copy()
    for col in LLM_COLUMNS:
        df[col] = None

    # Defaults for non-meaningful
    non_meaningful = df["text_quality"] != "Meaningful"
    for idx in df[non_meaningful].index:
        rating = df.loc[idx, "star_rating"] if "star_rating" in df.columns else 3
        for col, val in _get_default_llm_fields(rating).items():
            df.at[idx, col] = val

    meaningful_df = df[df["text_quality"] == "Meaningful"]
    if len(meaningful_df) == 0:
        return df

    cache = st.session_state.get("llm_cache", {})
    uncached = []
    for idx in meaningful_df.index:
        text = str(df.loc[idx, "cleaned_review_text"] or df.loc[idx, "review_text"] or "")
        ck = _cache_key(text)
        if ck in cache:
            for col, val in cache[ck].items():
                df.at[idx, col] = val
        else:
            uncached.append(idx)

    if not uncached:
        if progress_callback:
            progress_callback(1.0, "All reviews loaded from cache!")
        return df

    client = get_openai_client(api_key)
    processed = 0
    for batch_start in range(0, len(uncached), batch_size):
        batch_idx = uncached[batch_start:batch_start + batch_size]
        batch_reviews = []
        for idx in batch_idx:
            batch_reviews.append({
                "star_rating": df.loc[idx, "star_rating"] if "star_rating" in df.columns else 3,
                "cleaned_review_text": str(df.loc[idx, "cleaned_review_text"] if pd.notna(df.loc[idx, "cleaned_review_text"]) else df.loc[idx, "review_text"]),
            })
        results = _call_llm_with_retry(client, model, batch_reviews)
        for i, idx in enumerate(batch_idx):
            r = results[i] if i < len(results) else _get_default_llm_fields()
            validated = _validate_result(r)
            text = str(df.loc[idx, "cleaned_review_text"] or df.loc[idx, "review_text"] or "")
            cache[_cache_key(text)] = validated
            for col, val in validated.items():
                df.at[idx, col] = val
        processed += len(batch_idx)
        if progress_callback:
            progress_callback(processed / len(uncached), f"Processed {processed}/{len(uncached)} reviews...")

    st.session_state["llm_cache"] = cache
    return df


def estimate_cost(meaningful_count, model=DEFAULT_MODEL):
    total_batches = (meaningful_count + BATCH_SIZE - 1) // BATCH_SIZE
    avg_in, avg_out = 200, 100
    total_in = meaningful_count * avg_in + total_batches * 150
    total_out = meaningful_count * avg_out
    if "gpt-4o-mini" in model:
        cost = total_in * 0.15 / 1e6 + total_out * 0.6 / 1e6
    elif "gpt-4o" in model:
        cost = total_in * 2.5 / 1e6 + total_out * 10.0 / 1e6
    else:
        cost = total_in * 0.5 / 1e6 + total_out * 1.5 / 1e6
    return {"total_batches": total_batches, "estimated_cost_usd": round(cost, 4),
            "meaningful_reviews": meaningful_count, "model": model}
