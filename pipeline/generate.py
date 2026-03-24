import json
import ollama
from pathlib import Path
from pydantic import BaseModel

MODEL = "llama3.1:8b"
DATA_FILE = Path("data/posts.jsonl")


class Author(BaseModel):
    displayName: str
    uuid: str


class Post(BaseModel):
    text: str
    author: Author
    publishedDate: int


class PostList(BaseModel):
    posts: list[Post]


def generate(count: int, theme: str, languages: list[str] | None = None):
    language_instruction = ""
    if languages:
        lang_list = ", ".join(languages)
        language_instruction = (
            f" Distribute the posts across these languages: {lang_list}."
            f" Write each post naturally in its assigned language."
            f" Use culturally appropriate names for authors."
        )

    prompt = (
        f"Generate {count} realistic social media posts about the topic: \"{theme}\"."
        f"{language_instruction}"
        f" Each post must have a text (1-3 sentences), an author with displayName and uuid, "
        f"and a publishedDate as a Unix timestamp from the past 30 days."
    )

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format=PostList.model_json_schema(),
    )

    result = PostList.model_validate_json(response.message.content)

    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        for post in result.posts:
            f.write(json.dumps(post.model_dump(), ensure_ascii=False) + "\n")

    print(f"    Saved {len(result.posts)} posts to {DATA_FILE}")
