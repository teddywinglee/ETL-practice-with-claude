import json
import pytest
from pipeline.extract import extract, _validate_post


def _post(text="Hello world!", name="Alice", uuid="abc-123", ts=1000):
    return {"text": text, "author": {"displayName": name, "uuid": uuid}, "publishedDate": ts}


def write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


# ---------------------------------------------------------------------------
# Existing tests (updated to use valid Post schema)
# ---------------------------------------------------------------------------

def test_extract_returns_all_records(tmp_path):
    posts = [_post("post 1"), _post("post 2")]
    f = tmp_path / "posts.jsonl"
    write_jsonl(f, posts)
    assert extract(f) == posts


def test_extract_skips_blank_lines(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text(
        json.dumps(_post("a")) + "\n\n" + json.dumps(_post("b")) + "\n",
        encoding="utf-8",
    )
    assert len(extract(f)) == 2


def test_extract_empty_file(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text("", encoding="utf-8")
    assert extract(f) == []


def test_extract_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nonexistent.jsonl")


# ---------------------------------------------------------------------------
# Guardrail: malformed JSON
# ---------------------------------------------------------------------------

def test_extract_skips_malformed_json(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text(
        json.dumps(_post("good post")) + "\n"
        + "this is not json\n"
        + json.dumps(_post("another good post")) + "\n",
        encoding="utf-8",
    )
    result = extract(f)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Guardrail: schema validation
# ---------------------------------------------------------------------------

def test_validate_post_accepts_valid():
    assert _validate_post(_post(), line_num=1) is None


def test_validate_post_rejects_missing_author():
    assert _validate_post({"text": "hello", "publishedDate": 1}, line_num=1) is not None


def test_validate_post_rejects_missing_text():
    assert _validate_post({"author": {"displayName": "A", "uuid": "1"}, "publishedDate": 1}, line_num=1) is not None


def test_extract_skips_invalid_schema(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text(
        json.dumps(_post("good")) + "\n"
        + json.dumps({"text": "no author"}) + "\n",
        encoding="utf-8",
    )
    result = extract(f)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Guardrail: empty text
# ---------------------------------------------------------------------------

def test_validate_post_rejects_empty_text():
    assert _validate_post(_post(text=""), line_num=1) is not None


def test_validate_post_rejects_whitespace_text():
    assert _validate_post(_post(text="   "), line_num=1) is not None


# ---------------------------------------------------------------------------
# Guardrail: duplicate detection
# ---------------------------------------------------------------------------

def test_extract_deduplicates_by_text(tmp_path):
    f = tmp_path / "posts.jsonl"
    write_jsonl(f, [_post("same text", name="Alice"), _post("same text", name="Bob"), _post("different text")])
    result = extract(f)
    assert len(result) == 2
    assert result[0]["author"]["displayName"] == "Alice"  # keeps first occurrence
