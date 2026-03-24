import json
from pathlib import Path

DATA_FILE = Path("data/posts.jsonl")


def extract(path: Path = DATA_FILE) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        posts = [json.loads(line) for line in f if line.strip()]

    print(f"    Loaded {len(posts)} posts from {path}")
    return posts
