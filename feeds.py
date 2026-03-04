# feeds.py
import feedparser
from datetime import datetime, timezone, timedelta

FEED_URLS = [
    "https://www.statnews.com/feed/",
    "https://www.fiercepharma.com/rss/xml",
    "https://www.technologyreview.com/feed/",
    "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
    "https://www.science.org/blog/pipeline/feed",
]

KEYWORDS = [
    "AI", "machine learning", "LLM", "FDA", "GMP", "pharma",
    "biotech", "DEA", "manufacturing", "compliance", "clinical", "regulatory",
]

def is_recent(entry, hours=24):
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            published = datetime(*t[:6], tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - published <= timedelta(hours=hours)
    return False

def is_relevant(entry):
    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def fetch_feeds():
    articles = []
    for url in FEED_URLS:
        try:
            feed = feedparser.parse(url)
            source = feed.feed.get("title", url)
            for entry in feed.entries:
                if not is_recent(entry):
                    continue
                if not is_relevant(entry):
                    continue
                articles.append({
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", "").strip(),
                    "url": entry.get("link", ""),
                    "source": source,
                    "published": entry.get("published", entry.get("updated", "")),
                })
        except Exception as e:
            print(f"[feeds] Skipping {url}: {e}")
            continue
    return articles
