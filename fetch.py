import json, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

data = {
    "village": [],
    "news": [],
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

# 1. Fetch English Czech News (Radio Prague International - confirmed working!)
try:
    feed = feedparser.parse("https://radio.cz")
    for entry in feed.entries[:8]:
        published = getattr(entry, "published", "")[:16]
        data["news"].append({
            "title": entry.title,
            "link": entry.link,
            "meta": f"Radio Prague • {published}" if published else "Radio Prague"
        })
except Exception as e:
    print("News error:", e)

# 2. Fetch Obec Zelenec News with full browser headers
try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
        "Referer": "https://www.zelenec.cz/"
    }
    vr = requests.get("https://www.zelenec.cz/aktuality", headers=headers, timeout=15)
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
