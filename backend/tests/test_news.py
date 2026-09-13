from app.news.service import _deduplicate, _score

def test_news_sentiment_is_deterministic():
    assert _score('Bitcoin rally gains momentum') == 'bullish'
    assert _score('Bitcoin price falls after hack') == 'bearish'
    assert _score('Bitcoin trades in a range') == 'neutral'

def test_news_items_are_deduplicated_by_title_and_url():
    articles = [{'title': 'Gold rally', 'url': 'https://example.test/a', 'source': {'name': 'A'}}, {'title': 'Gold rally', 'url': 'https://example.test/a', 'source': {'name': 'A'}}]
    assert len(_deduplicate(articles)) == 1
