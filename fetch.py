import json, os, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

existing = {"village": [], "news": []}
if os.path.exists("data.json"):
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

data = {
    "village": existing.get("village", []),
    "news": existing.get("news", []),
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

# 1. Fetch English Czech News (Radio Prague International)
try:
    feed = feedparser.parse("https://radio.cz")
    new_articles = []
    for entry in feed.entries[:8]:
        published = getattr(entry, "published", "")[:16]
        new_articles.append({
            "title": entry.title.strip(),
            "link": entry.link.strip(),
            "meta": f"Radio Prague • {published}" if published else "Radio Prague"
        })
    if new_articles:
        data["news"] = new_articles
except Exception as e:
    print("News error:", e)

# 2. Fetch Obec Zelenec News (check /aktuality and /uredni-deska)
new_village = []
seen = set()
for page_url in ["https://zelenec.cz", "https://zelenec.cz"]:
    try:
        vr = requests.get(page_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(vr.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = " ".join(a.get_text().split())
            # Match news or official board links with real titles
            if ("/aktuality/" in href or "/uredni-deska/" in href) and len(href) > 15 and "page=" not in href and "filter-" not in href:
                link = href if href.startswith("http") else "https://zelenec.cz" + href
                if len(title) > 10 and link not in seen:
                    seen.add(link)
                    new_village.append({
                        "title": title,
                        "link": link,
                        "date": "Obec Zeleneč"
                    })
                    if len(new_village) >= 6:
                        break
        if new_village:
            data["village"] = new_village
            break
    except Exception as e:
        print("Village error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> village: {len(data['village'])}, news: {len(data['news'])}")
