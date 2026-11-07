import json, os, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

# Load existing data.json so temporary rate limits never wipe out working news
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

# 1. Fetch English Czech News (Radio Prague + Google News EN fallback)
new_articles = []
for source_name, url in [
    ("Radio Prague", "https://radio.cz"),
    ("Czech News", "https://google.com")
]:
    try:
        nr = requests.get(url, headers=HEADERS, timeout=15)
        if nr.status_code == 200 and len(nr.content) > 200:
            feed = feedparser.parse(nr.content)
            for entry in feed.entries[:8]:
                published = getattr(entry, "published", "")[:16]
                new_articles.append({
                    "title": entry.title.split(" - ")[0].strip(),
                    "link": entry.link,
                    "meta": f"{source_name} • {published}" if published else source_name
                })
            if new_articles:
                data["news"] = new_articles
                break
    except Exception as e:
        print("News error:", e)

# 2. Fetch Obec Zelenec News (check both homepage and /aktuality)
new_village = []
seen = set()
for page_url in ["https://zelenec.cz", "https://zelenec.czaktuality"]:
    try:
        vr = requests.get(page_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(vr.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/aktuality/" in href and len(href) > 15 and "page=" not in href:
                title = " ".join(a.get_text().split())
                link = href if href.startswith("http") else "https://zelenec.cz" + href
                if len(title) > 8 and link not in seen:
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
