from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import feedparser
import time

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
RSS_SOURCES = [
    {
        "name": "BBC Bangla",
        "category": "news",
        "rss": "https://feeds.bbci.co.uk/bengali/rss.xml"
    }
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (NewsAggregatorBot)"
}

# simple in-memory cache (Railway restart হলে reset হবে)
CACHE = {}
CACHE_TTL = 300  # 5 minutes


# =========================
# UTILITIES
# =========================
def is_cache_valid(key):
    if key not in CACHE:
        return False
    return (time.time() - CACHE[key]["time"]) < CACHE_TTL


def set_cache(key, data):
    CACHE[key] = {
        "time": time.time(),
        "data": data
    }


# =========================
# SCRAPING
# =========================
def scrape_article_details(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        # Title
        title = soup.find("meta", property="og:title")
        title = title["content"] if title else soup.title.string if soup.title else ""

        # Thumbnail
        image = soup.find("meta", property="og:image")
        image = image["content"] if image else ""

        # Description / summary
        desc = soup.find("meta", property="og:description")
        summary = desc["content"] if desc else ""

        return title.strip(), image.strip(), summary.strip()

    except Exception:
        return "", "", ""


# =========================
# RSS + SCRAPE HYBRID
# =========================
def fetch_rss_news(limit=10):
    articles = []

    for source in RSS_SOURCES:
        feed = feedparser.parse(source["rss"])

        for entry in feed.entries[:limit]:
            link = entry.get("link", "")
            published = entry.get("published", "")

            title, image, summary = scrape_article_details(link)

            articles.append({
                "title": title or entry.get("title", ""),
                "url": link,
                "thumbnail": image,
                "summary": summary,
                "source": source["name"],
                "category": source["category"],
                "published": published
            })

    return articles


# =========================
# API ROUTE
# =========================
@app.route("/news")
def get_news():
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))

    cache_key = f"{category}_{page}_{limit}"

    if is_cache_valid(cache_key):
        return jsonify(CACHE[cache_key]["data"])

    all_articles = fetch_rss_news(limit=20)

    if category:
        all_articles = [
            a for a in all_articles if a["category"] == category
        ]

    start = (page - 1) * limit
    end = start + limit
    paginated = all_articles[start:end]

    response = {
        "count": len(paginated),
        "articles": paginated
    }

    set_cache(cache_key, response)
    return jsonify(response)


# =========================
# ROOT (optional)
# =========================
@app.route("/")
def home():
    return {"status": "News API running"}


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
