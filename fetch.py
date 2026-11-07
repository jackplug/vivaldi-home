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

# 1. Fetch English Czech News (tries Radio Prague, Expats.cz, and Prague Morning)
rss_sources = [
    ("Radio Prague", "https://radio.cz"),
    ("Expats.cz", "https://expats.cz"),
    ("Prague Morning", "https://praguemorning.cz")
]
for source_name, url in rss_sources:
    try:
        nr = requests.get(url, headers=HEADERS, timeout=15)
        if nr.status_code == 200 and len(nr.content) > 200:
            feed = feedparser.parse(nr.content)
            new_articles = []
            for entry in feed.entries[:8]:
                published = getattr(entry, "published", "")[:16]
                new_articles.append({
                    "title": entry.title.strip(),
                    "link": entry.link.strip(),
                    "meta": f"{source_name} • {published}" if published else source_name
                })
            if new_articles:
                data["news"] = new_articles
                print(f"Loaded {len(new_articles)} articles from {source_name}")
                break
    except Exception as e:
        print(f"News error ({source_name}):", e)

# 2. Fetch Obec Zelenec News (scans main content area & headings on zelenec.cz)
try:
    vr = requests.get("https://zelenec.cz", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(vr.text, "html.parser")
    new_village = []
    seen = set()

    # Check links inside <main>, <article>, or headings first (avoids top nav menu)
    container = soup.find("main") or soup
    skip_words = {"přeskočit", "zastupitelstvo", "výbory", "veřejné zakázky", "hospodaření", "vyhlášky", "povinně", "mstětice", "kontakty", "úřední deska", "aktuality", "kalendář", "fotogalerie"}
    for a in container.find_all("a", href=True):
        href = a["href"]
        title = " ".join(a.get_text().split())
        low = title.lower()
        if (
            href.startswith("/")
            and len(href) > 12
            and len(title) > 14
            and not any(w in low for w in skip_words)
            and "filter-" not in href
            and "page=" not in href
        ):
            link = "https://zelenec.cz" + href
            if link not in seen:
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
except Exception as e:
    print("Village error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> village: {len(data['village'])}, news: {len(data['news'])}")
