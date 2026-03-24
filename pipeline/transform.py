import ollama
from collections import defaultdict
from typing import Literal
from pydantic import BaseModel

MODEL = "llama3.1:8b"


class PostTag(BaseModel):
    topic: str
    sentiment: Literal["positive", "neutral", "negative"]
    language: str  # e.g. "English", "Mandarin", "Spanish"


class TopicEntry(BaseModel):
    original: str
    canonical: str


class TopicMergeResult(BaseModel):
    mappings: list[TopicEntry]


def tag_post(post: dict) -> PostTag:
    response = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"Analyze this social media post.\n\n"
                f"Post: \"{post['text']}\"\n\n"
                f"Detect the language of the post (return the language name only, e.g. 'English', 'Mandarin', 'Spanish'). "
                f"Return a topic label (2-4 words) and sentiment. "
                f"Always respond in English regardless of the post's language."
            )
        }],
        format=PostTag.model_json_schema(),
    )
    return PostTag.model_validate_json(response.message.content)


def merge_topics(topics: list[str]) -> dict[str, str]:
    topics_list = "\n".join(f"- {t}" for t in topics)
    response = ollama.chat(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                f"Group these similar topic labels under canonical names (2-4 words each). "
                f"Keep distinct topics as-is.\n\n{topics_list}"
            )
        }],
        format=TopicMergeResult.model_json_schema(),
    )
    result = TopicMergeResult.model_validate_json(response.message.content)
    return {entry.original: entry.canonical for entry in result.mappings}


def summarize_cluster(topic: str, posts: list[dict]) -> str:
    posts_text = "\n".join(f"- {p['text']}" for p in posts)
    response = ollama.chat(
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
    return response.message.content.strip()


def transform(posts: list[dict]) -> dict:
    # Step 1: tag each post individually
    print(f"    Tagging {len(posts)} posts...")
    tagged = []
    for i, post in enumerate(posts):
        tag = tag_post(post)
        tagged.append({**post, "topic": tag.topic, "sentiment": tag.sentiment, "language": tag.language})
        print(f"    [{i+1}/{len(posts)}] {post['author']['displayName']}: {tag.topic} ({tag.sentiment}, {tag.language})")

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

    # Step 4: summarize each cluster
    print(f"    Summarizing {len(clusters)} topic(s)...")
    report_clusters = []
    for topic, cluster_posts in sorted(clusters.items(), key=lambda x: -len(x[1])):
        summary = summarize_cluster(topic, cluster_posts)
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
        "total_posts": len(posts),
        "total_topics": len(clusters),
        "language_counts": language_counts,
        "clusters": report_clusters,
    }
