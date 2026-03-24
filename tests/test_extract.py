import json
import pytest
from pipeline.extract import extract


def write_jsonl(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")


def test_extract_returns_all_records(tmp_path):
    posts = [{"text": "post 1"}, {"text": "post 2"}]
    f = tmp_path / "posts.jsonl"
    write_jsonl(f, posts)
    assert extract(f) == posts


def test_extract_skips_blank_lines(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text('{"text": "a"}\n\n{"text": "b"}\n', encoding="utf-8")
    assert len(extract(f)) == 2


def test_extract_empty_file(tmp_path):
    f = tmp_path / "posts.jsonl"
    f.write_text("", encoding="utf-8")
    assert extract(f) == []


def test_extract_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract(tmp_path / "nonexistent.jsonl")
