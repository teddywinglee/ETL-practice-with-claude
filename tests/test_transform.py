from unittest.mock import patch
from pipeline.transform import PostTag, transform


POSTS = [
    {"text": "EVs are great!", "author": {"displayName": "Alice", "uuid": "1"}, "publishedDate": 1},
    {"text": "Charging is slow.", "author": {"displayName": "Bob", "uuid": "2"}, "publishedDate": 2},
    {"text": "Battery range improved.", "author": {"displayName": "Carol", "uuid": "3"}, "publishedDate": 3},
]


def make_tag(topic, sentiment, language="English"):
    return PostTag(topic=topic, sentiment=sentiment, language=language)


@patch("pipeline.transform.summarize_cluster", return_value="A summary.")
@patch("pipeline.transform.merge_topics", return_value={"EV Benefits": "EV Benefits", "Charging Issues": "Charging Issues"})
@patch("pipeline.transform.tag_post", side_effect=[
    make_tag("EV Benefits", "positive"),
    make_tag("Charging Issues", "negative"),
    make_tag("EV Benefits", "positive"),
])
def test_transform_clusters_by_topic(mock_tag, mock_merge, mock_summarize):
    result = transform(POSTS)
    topics = [c["topic"] for c in result["clusters"]]
    assert "EV Benefits" in topics
    assert "Charging Issues" in topics


@patch("pipeline.transform.summarize_cluster", return_value="A summary.")
@patch("pipeline.transform.merge_topics", return_value={"EV Benefits": "EV Benefits", "Charging Issues": "Charging Issues"})
@patch("pipeline.transform.tag_post", side_effect=[
    make_tag("EV Benefits", "positive"),
    make_tag("Charging Issues", "negative"),
    make_tag("EV Benefits", "positive"),
])
def test_transform_sentiment_breakdown(mock_tag, mock_merge, mock_summarize):
    result = transform(POSTS)
    ev_cluster = next(c for c in result["clusters"] if c["topic"] == "EV Benefits")
    assert ev_cluster["sentiment_breakdown"]["positive"] == 2
    assert ev_cluster["sentiment_breakdown"]["negative"] == 0


@patch("pipeline.transform.summarize_cluster", return_value="A summary.")
@patch("pipeline.transform.merge_topics", return_value={"EV Benefits": "EV Benefits", "Charging Issues": "Charging Issues"})
@patch("pipeline.transform.tag_post", side_effect=[
    make_tag("EV Benefits", "positive"),
    make_tag("Charging Issues", "negative"),
    make_tag("EV Benefits", "positive"),
])
def test_transform_totals(mock_tag, mock_merge, mock_summarize):
    result = transform(POSTS)
    assert result["total_posts"] == 3
    assert result["total_topics"] == 2
