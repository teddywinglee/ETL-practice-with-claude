from pipeline.load import _dominant_sentiment


def make_cluster(pos, neu, neg):
    return {"sentiment_breakdown": {"positive": pos, "neutral": neu, "negative": neg}}


def test_dominant_sentiment_positive():
    clusters = [make_cluster(10, 2, 1)]
    assert _dominant_sentiment(clusters) == "Positive"


def test_dominant_sentiment_negative():
    clusters = [make_cluster(1, 2, 10)]
    assert _dominant_sentiment(clusters) == "Negative"


def test_dominant_sentiment_aggregates_across_clusters():
    clusters = [make_cluster(5, 0, 0), make_cluster(0, 0, 8)]
    assert _dominant_sentiment(clusters) == "Negative"


def test_dominant_sentiment_neutral():
    clusters = [make_cluster(1, 5, 1)]
    assert _dominant_sentiment(clusters) == "Neutral"
