from unittest.mock import patch, MagicMock
from langdetect import LangDetectException
from pipeline.transform import (
    PostTag, transform,
    _validate_topic, _cross_check_language, _llm_call_with_retry,
)


POSTS = [
    {"text": "EVs are great!", "author": {"displayName": "Alice", "uuid": "1"}, "publishedDate": 1},
    {"text": "Charging is slow.", "author": {"displayName": "Bob", "uuid": "2"}, "publishedDate": 2},
    {"text": "Battery range improved.", "author": {"displayName": "Carol", "uuid": "3"}, "publishedDate": 3},
]


def make_tag(topic, sentiment, language="English"):
    return PostTag(topic=topic, sentiment=sentiment, language=language)


# ---------------------------------------------------------------------------
# Existing orchestration tests
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Guardrail: retry with backoff
# ---------------------------------------------------------------------------

@patch("pipeline.transform.time.sleep")
@patch("pipeline.transform.lm_studio.chat.completions.create")
def test_retry_succeeds_on_second_attempt(mock_create, mock_sleep):
    mock_create.side_effect = [ConnectionError("timeout"), MagicMock(choices=[MagicMock(message=MagicMock(content='{"text":"ok"}'))])]
    result = _llm_call_with_retry(model="test", messages=[])
    assert mock_create.call_count == 2
    mock_sleep.assert_called_once_with(1)  # 2**0 = 1


@patch("pipeline.transform.time.sleep")
@patch("pipeline.transform.lm_studio.chat.completions.create", side_effect=ConnectionError("down"))
def test_retry_exhausted_raises(mock_create, mock_sleep):
    try:
        _llm_call_with_retry(model="test", messages=[])
        assert False, "Should have raised"
    except ConnectionError:
        pass
    assert mock_create.call_count == 3


# ---------------------------------------------------------------------------
# Guardrail: topic label quality gate
# ---------------------------------------------------------------------------

def test_validate_topic_rejects_vague():
    assert _validate_topic("General") is False
    assert _validate_topic("Other") is False
    assert _validate_topic("miscellaneous") is False
    assert _validate_topic("N/A") is False


def test_validate_topic_rejects_long():
    assert _validate_topic("This Is A Very Long Topic Label Here") is False


def test_validate_topic_accepts_good():
    assert _validate_topic("Electric Vehicle Adoption") is True
    assert _validate_topic("Battery Tech") is True


@patch("pipeline.transform._cross_check_language", return_value="English")
@patch("pipeline.transform._llm_call_with_retry")
def test_tag_post_retries_on_vague_topic(mock_llm, mock_lang):
    vague_response = MagicMock(choices=[MagicMock(message=MagicMock(content='{"topic":"General","sentiment":"positive","language":"English"}'))])
    good_response = MagicMock(choices=[MagicMock(message=MagicMock(content='{"topic":"EV Adoption","sentiment":"positive","language":"English"}'))])
    mock_llm.side_effect = [vague_response, good_response]

    from pipeline.transform import tag_post
    result = tag_post({"text": "EVs are the future!", "author": {"displayName": "A", "uuid": "1"}})

    assert result.topic == "EV Adoption"
    assert mock_llm.call_count == 2


# ---------------------------------------------------------------------------
# Guardrail: language cross-check
# ---------------------------------------------------------------------------

@patch("pipeline.transform.detect", return_value="en")
def test_cross_check_language_match(mock_detect, capsys):
    result = _cross_check_language("Hello world", "English")
    assert result == "English"
    assert "[lang-check]" not in capsys.readouterr().out


@patch("pipeline.transform.detect", return_value="es")
def test_cross_check_language_mismatch(mock_detect, capsys):
    result = _cross_check_language("Hola mundo", "English")
    assert result == "English"  # always returns LLM's answer
    assert "[lang-check]" in capsys.readouterr().out


@patch("pipeline.transform.detect", side_effect=LangDetectException(0, "too short"))
def test_cross_check_language_short_text(mock_detect):
    result = _cross_check_language("Hi", "English")
    assert result == "English"  # no crash


# ---------------------------------------------------------------------------
# Guardrail: graceful degradation
# ---------------------------------------------------------------------------

@patch("pipeline.transform.summarize_cluster", return_value="A summary.")
@patch("pipeline.transform.merge_topics", return_value={"EV Benefits": "EV Benefits"})
@patch("pipeline.transform.tag_post", side_effect=[
    make_tag("EV Benefits", "positive"),
    Exception("LLM timeout"),
    make_tag("EV Benefits", "neutral"),
])
def test_transform_skips_failed_post(mock_tag, mock_merge, mock_summarize):
    result = transform(POSTS)
    assert result["total_posts"] == 2  # 1 skipped


@patch("pipeline.transform.summarize_cluster", side_effect=Exception("LLM error"))
@patch("pipeline.transform.merge_topics", return_value={"EV Benefits": "EV Benefits"})
@patch("pipeline.transform.tag_post", side_effect=[
    make_tag("EV Benefits", "positive"),
    make_tag("EV Benefits", "negative"),
    make_tag("EV Benefits", "neutral"),
])
def test_transform_fallback_summary(mock_tag, mock_merge, mock_summarize):
    result = transform(POSTS)
    summary = result["clusters"][0]["summary"]
    assert "Summary unavailable" in summary
