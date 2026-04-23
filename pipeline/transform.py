import time

from collections import defaultdict
from typing import Literal
from pydantic import BaseModel
from langdetect import detect, LangDetectException
from pipeline.config import MODEL, lm_studio

MAX_RETRIES = 3

VAGUE_TOPICS = {
    "general", "other", "miscellaneous", "various", "misc",
    "n/a", "none", "topic", "unknown",
}

LANG_CODE_MAP = {
    "en": "English", "zh-cn": "Mandarin", "zh-tw": "Mandarin",
    "es": "Spanish", "fr": "French", "de": "German",
    "ja": "Japanese", "ko": "Korean", "pt": "Portuguese", "ar": "Arabic",
}


class PostTag(BaseModel):
    topic: str
    sentiment: Literal["positive", "neutral", "negative"]
    language: str  # e.g. "English", "Mandarin", "Spanish"


class TopicEntry(BaseModel):
    original: str
    canonical: str


class TopicMergeResult(BaseModel):
    mappings: list[TopicEntry]


# ---------------------------------------------------------------------------
# Guardrail helpers
# ---------------------------------------------------------------------------

def _llm_call_with_retry(**kwargs):
    """Call lm_studio.chat.completions.create() with exponential-backoff retry on transient failures."""
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            return lm_studio.chat.completions.create(**kwargs)
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                print(f"    [retry {attempt+1}/{MAX_RETRIES}] {type(e).__name__}: {e} — retrying in {wait}s")
                time.sleep(wait)
    raise last_err


def _validate_topic(label: str) -> bool:
    """Reject vague or overly long topic labels."""
    stripped = label.strip().lower()
    if stripped in VAGUE_TOPICS:
        return False
    if len(label.split()) > 6:
        return False
    return True


def _cross_check_language(text: str, llm_language: str) -> str:
    """Log a warning if langdetect disagrees with the LLM's language label."""
    try:
        code = detect(text)
        detected = LANG_CODE_MAP.get(code, code)
        if detected.lower() != llm_language.lower():
            print(f"    [lang-check] LLM said '{llm_language}', langdetect says '{detected}' for: {text[:60]}...")
    except LangDetectException:
        pass  # too short or ambiguous — not actionable
    return llm_language


# ---------------------------------------------------------------------------
# Core LLM functions
# ---------------------------------------------------------------------------

def tag_post(post: dict) -> PostTag:
    base_prompt = (
        f"Analyze this social media post.\n\n"
        f"Post: \"{post['text']}\"\n\n"
        f"Detect the language of the post (return the language name only, e.g. 'English', 'Mandarin', 'Spanish'). "
        f"Return a topic label (2-4 words) and sentiment. "
        f"Always respond in English regardless of the post's language."
    )
    nudge = " Be specific — avoid generic labels like 'General' or 'Other'. Use 2-4 descriptive words."

    tag = None
    for attempt in range(MAX_RETRIES):
        prompt = base_prompt if attempt == 0 else base_prompt + nudge
        response = _llm_call_with_retry(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "PostTag", "schema": PostTag.model_json_schema()},
            },
        )
        tag = PostTag.model_validate_json(response.choices[0].message.content)

        if _validate_topic(tag.topic):
            break
        if attempt < MAX_RETRIES - 1:
            print(f"    [topic-check] Vague topic '{tag.topic}' — retrying with stricter prompt")

    _cross_check_language(post["text"], tag.language)
    return tag


def merge_topics(topics: list[str]) -> dict[str, str]:
    topics_list = "\n".join(f"- {t}" for t in topics)
    response = _llm_call_with_retry(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"Group these similar topic labels under canonical names (2-4 words each). "
                f"Keep distinct topics as-is.\n\n{topics_list}"
            )
        }],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "TopicMergeResult", "schema": TopicMergeResult.model_json_schema()},
        },
    )
    result = TopicMergeResult.model_validate_json(response.choices[0].message.content)
    return {entry.original: entry.canonical for entry in result.mappings}


def summarize_cluster(topic: str, posts: list[dict]) -> str:
    posts_text = "\n".join(f"- {p['text']}" for p in posts)
    response = _llm_call_with_retry(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"You are writing a section of an industry report based on social media posts.\n\n"
                f"Topic: {topic}\nPosts:\n{posts_text}\n\n"
                f"Write 2-3 sentences summarizing what people are saying, key points of discussion, "
                f"and any notable trends or concerns. Be analytical and concise."
            )
        }],
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def transform(posts: list[dict]) -> dict:
    # Step 1: tag each post individually (skip failures gracefully)
    print(f"    Tagging {len(posts)} posts...")
    tagged = []
    for i, post in enumerate(posts):
        try:
            tag = tag_post(post)
            tagged.append({**post, "topic": tag.topic, "sentiment": tag.sentiment, "language": tag.language})
            print(f"    [{i+1}/{len(posts)}] {post['author']['displayName']}: {tag.topic} ({tag.sentiment}, {tag.language})")
        except Exception as e:
            print(f"    [skip] Failed to tag post by {post['author']['displayName']}: {e}")
            continue

    if not tagged:
        raise RuntimeError("All posts failed tagging — nothing to transform")

    # Step 2: merge similar topic labels into canonical ones
    unique_topics = list({p["topic"] for p in tagged})
    print(f"    Merging {len(unique_topics)} raw topic(s) into canonical labels...")
    topic_map = merge_topics(unique_topics)
    for post in tagged:
        post["topic"] = topic_map.get(post["topic"], post["topic"])

    # Step 3: group by canonical topic
    clusters = defaultdict(list)
    for post in tagged:
        clusters[post["topic"]].append(post)

    # Step 4: summarize each cluster (fallback on failure)
    print(f"    Summarizing {len(clusters)} topic(s)...")
    report_clusters = []
    for topic, cluster_posts in sorted(clusters.items(), key=lambda x: -len(x[1])):
        try:
            summary = summarize_cluster(topic, cluster_posts)
        except Exception as e:
            print(f"    [fallback] Summary failed for '{topic}': {e}")
            summary = f"Summary unavailable for {topic} ({len(cluster_posts)} posts)."

        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        for p in cluster_posts:
            sentiment_counts[p.get("sentiment", "neutral")] += 1

        report_clusters.append({
            "topic": topic,
            "post_count": len(cluster_posts),
            "sentiment_breakdown": sentiment_counts,
            "summary": summary,
            "posts": cluster_posts,
        })

    language_counts: dict[str, int] = {}
    for post in tagged:
        lang = post.get("language", "Unknown")
        language_counts[lang] = language_counts.get(lang, 0) + 1

    return {
        "total_posts": len(tagged),
        "total_topics": len(clusters),
        "language_counts": language_counts,
        "clusters": report_clusters,
    }
