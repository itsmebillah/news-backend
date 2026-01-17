from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import feedparser
import time
import datetime

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
RSS_SOURCES = [
    # News - General / Reliable
    {"name": "BBC Bangla", "category": "news", "rss": "https://feeds.bbci.co.uk/bengali/rss.xml"},
    {"name": "Prothom Alo", "category": "news", "rss": "https://www.prothomalo.com/feed/"},
    {"name": "Jugantor", "category": "news", "rss": "https://www.jugantor.com/rss/latest"},
    {"name": "Kaler Kantho", "category": "news", "rss": "https://www.kalerkantho.com/rss.xml"},
    {"name": "RisingBD", "category": "news", "rss": "https://www.risingbd.com/rss/rss.xml"},
    {"name": "BD24Live", "category": "news", "rss": "https://www.bd24live.com/feed"},

    # Jobs / চাকরি (dedicated RSS কম, general feed + category filter)
    {"name": "BD Govt Job (via aggregator)", "category": "jobs", "rss": "https://bdgovtjob.net/feed/"},
    {"name": "Prothom Alo (filter jobs)", "category": "jobs", "rss": "https://www.prothomalo.com/feed/"},

    # Education / শিক্ষা
    {"name": "Prothom Alo (filter education)", "category": "education", "rss": "https://www.prothomalo.com/feed/"},
    {"name": "Jagonews24", "category": "education", "rss": "https://www.jagonews24.com/rss/rss.xml"},

    # Tech
    {"name": "Prothom Alo Tech", "category": "tech", "rss": "https://www.prothomalo.com/feed/"},
    {"name": "Jugantor Tech", "category": "tech", "rss": "https://www.jugantor.com/rss/tech"},
]
# Simple in-memory cache
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

def parse_published(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
    except:
        return None

# =========================
# SCRAPING
# =========================
def scrape_article_details(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Title fallback chain
        title = soup.find("meta", property="og:title")
        title = title["content"] if title else soup.title.string if soup.title else "No Title"
        
        # Image fallback
        image = soup.find("meta", property="og:image")
        image = image["content"] if image else ""
        
        # Summary fallback
        desc = soup.find("meta", property="og:description")
        summary = desc["content"] if desc else soup.find("meta", {"name": "description"})["content"] if soup.find("meta", {"name": "description"}) else ""
        
        return title.strip(), image.strip(), summary.strip()
    except Exception as e:
        print(f"Scrape error: {e}")
        return "Error", "", "Failed to fetch details"

# =========================
# RSS + SCRAPE HYBRID
# =========================
def fetch_rss_news(limit=50):  # Fetch more for pagination
    articles = []
    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["rss"])
            for entry in feed.entries:
                link = entry.get("link", "")
                published_str = entry.get("published", "")
                published = parse_published(published_str)
                title, image, summary = scrape_article_details(link)
                articles.append({
                    "title": title or entry.get("title", "No Title"),
                    "url": link,
                    "thumbnail": image,
                    "summary": summary or entry.get("summary", ""),
                    "source": source["name"],
                    "category": source["category"],
                    "published": published_str,
                    "published_parsed": published
                })
        except Exception as e:
            print(f"RSS error for {source['name']}: {e}")
    
    # Sort by published date descending
    articles.sort(key=lambda x: x["published_parsed"] or datetime.datetime.min, reverse=True)
    return articles[:limit]

# =========================
# API ROUTE
# =========================
@app.route("/news")
def get_news():
    category = request.args.get("category", "")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    
    cache_key = f"news_{category}_{page}_{limit}"
    
    if is_cache_valid(cache_key):
        return jsonify(CACHE[cache_key]["data"])
    
    all_articles = fetch_rss_news(limit=page * limit + limit)  # Fetch extra for pagination
    
    if category:
        all_articles = [a for a in all_articles if a["category"] == category]
    
    start = (page - 1) * limit
    end = start + limit
    paginated = all_articles[start:end]
    
    response = {
        "count": len(paginated),
        "articles": paginated,
        "has_more": len(all_articles) > end
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

