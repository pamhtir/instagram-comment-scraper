"""Validation, normalization and deduplication for client-ready output."""

from __future__ import annotations

import pandas as pd


ORDERED_COLUMNS = [
    "platform", "content_type", "source_url", "comment_id", "username",
    "comment", "is_reply", "parent_username", "scraped_at_utc",
]
REQUIRED_COLUMNS = set(ORDERED_COLUMNS) - {"parent_username"}


def clean_comments(records: list[dict]) -> tuple[pd.DataFrame, dict[str, int]]:
    raw_count = len(records)
    if not records:
        empty = pd.DataFrame(columns=ORDERED_COLUMNS)
        return empty, {"raw": 0, "invalid": 0, "duplicates": 0, "final": 0}

    df = pd.DataFrame(records)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if "parent_username" not in df:
        df["parent_username"] = ""

    for column in ("username", "comment", "source_url", "parent_username"):
        df[column] = df[column].astype("string").fillna("").str.replace(r"\s+", " ", regex=True).str.strip()

    valid = (
        (df["username"] != "")
        & (df["comment"] != "")
        & (df["source_url"] != "")
        & (df["username"].str.len() <= 30)
        & df["username"].str.match(r"^[A-Za-z0-9._]+$", na=False)
        & (df["username"].str.casefold() != df["comment"].str.casefold())
    )
    invalid_count = int((~valid).sum())
    df = df.loc[valid].copy()
    before = len(df)
    df = df.drop_duplicates(subset=["comment_id"], keep="first")
    duplicate_count = before - len(df)
    df = df[ORDERED_COLUMNS].reset_index(drop=True)
    return df, {"raw": raw_count, "invalid": invalid_count, "duplicates": duplicate_count, "final": len(df)}
