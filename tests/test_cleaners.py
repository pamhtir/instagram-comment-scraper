import pytest

from src.cleaners import ORDERED_COLUMNS, clean_comments


def record(**changes):
    base = {"platform": "instagram", "content_type": "post", "source_url": "https://www.instagram.com/p/example/", "comment_id": "abc", "username": "demo.user", "comment": "Great post!", "scraped_at_utc": "2026-01-01T00:00:00+00:00", "is_reply": False, "parent_username": ""}
    return base | changes


def test_normalizes_whitespace():
    df, _ = clean_comments([record(comment="  Great   post!  ")])
    assert df.loc[0, "comment"] == "Great post!"


def test_removes_duplicate_ids():
    df, metrics = clean_comments([record(), record()])
    assert len(df) == 1 and metrics["duplicates"] == 1


@pytest.mark.parametrize("changes", [{"comment": "   "}, {"username": "invalid user"}, {"username": "same", "comment": "same"}])
def test_rejects_invalid_records(changes):
    df, metrics = clean_comments([record(**changes)])
    assert df.empty and metrics["invalid"] == 1


def test_missing_columns_raise_error():
    with pytest.raises(ValueError, match="Missing required columns"):
        clean_comments([{"username": "demo"}])


def test_empty_input_has_stable_schema():
    df, metrics = clean_comments([])
    assert list(df.columns) == ORDERED_COLUMNS and metrics["final"] == 0


def test_old_record_without_parent_username_is_compatible():
    item = record(); item.pop("parent_username")
    df, _ = clean_comments([item])
    assert df.loc[0, "parent_username"] == ""
