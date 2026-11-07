import json, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

data = {
    "village": [],
    "news": [],
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

# 1. Fetch English Czech News (Google News Czechia EN + Radio Prague fallback)
news_feeds = [
    ("Czech News", "https://google.com"),
    ("Radio Prague", "https://english.radio.cz/rcz-rss/en")
]
for source_name, url in news_feeds:
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:8]:
            title = entry.title.split(" - ")[0].strip()
            pub_source = entry.title.split(" - ")[-1].strip() if " - " in entry.title else source_name
            published = getattr(entry, "published", "")[:16]
            data["news"].append({
                "title": title,
                "link": entry.link,
                "meta": f"{pub_source} • {published}" if published else pub_source
            })
        if data["news"]:
            break
    except Exception as e:
        print("News error:", e)

# 2. Fetch Obec Zelenec News (from zelenec.cz/aktuality)
try:
    vr = requests.get(
        "https://www.zelenec.cz/aktuality",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"},
        timeout=15
    )
    soup = BeautifulSoup(vr.text, "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/aktuality/aktuality/" in href:
            title = " ".join(a.get_text().split())
            link = href if href.startswith("http") else "https://www.zelenec.cz" + href
            if len(title) > 6 and link not in seen:
                seen.add(link)
                data["village"].append({
                    "title": title,
                    "link": link,
                    "date": "Obec Zeleneč"
                })
                if len(data["village"]) >= 6:
                    break
except Exception as e:
    print("Village error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Done -> village: {len(data['village'])}, news: {len(data['news'])}")
