import json
from pathlib import Path

DATA_FILE = Path("data/posts.jsonl")


def extract() -> list[dict]:
    with open(DATA_FILE, encoding="utf-8") as f:
        posts = [json.loads(line) for line in f if line.strip()]

    print(f"    Loaded {len(posts)} posts from {DATA_FILE}")
    return posts
