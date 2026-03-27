import json
from pathlib import Path
from pydantic import ValidationError
from pipeline.generate import Post

DATA_FILE = Path("data/posts.jsonl")


def _validate_post(data: dict, line_num: int) -> str | None:
    """Return an error message if the post is invalid, or None if it's fine."""
    try:
        Post.model_validate(data)
    except ValidationError as e:
        return f"line {line_num}: schema validation failed — {e.error_count()} error(s)"

    if not data.get("text", "").strip():
        return f"line {line_num}: empty or whitespace-only text"

    return None


def extract(path: Path = DATA_FILE) -> list[dict]:
    posts = []
    seen_texts = set()
    skipped = 0

    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            if not line.strip():
                continue

            # Malformed JSON
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"    [skip] line {line_num}: malformed JSON — {e}")
                skipped += 1
                continue

            # Schema + content validation
            error = _validate_post(data, line_num)
            if error:
                print(f"    [skip] {error}")
                skipped += 1
                continue

            # Duplicate text detection
            text = data["text"].strip()
            if text in seen_texts:
                print(f"    [skip] line {line_num}: duplicate text — \"{text[:60]}...\"")
                skipped += 1
                continue
            seen_texts.add(text)

            posts.append(data)

    print(f"    Loaded {len(posts)} posts from {path}" + (f" ({skipped} skipped)" if skipped else ""))
    return posts
