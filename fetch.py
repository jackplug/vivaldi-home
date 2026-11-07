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

# 1. Fetch English Czech News (Radio Prague via feedparser + Google News EN fallback)
rp_url = "https://" + "english.radio.cz" + "/rcz-rss/en"
gn_url = "https://" + "://google.com" + "/rss/search?q=Czechia+OR+Prague&hl=en-US&gl=US&ceid=US:en"

for source_name, url in [("Radio Prague", rp_url), ("Czech News", gn_url)]:
    try:
        feed = feedparser.parse(url)
        new_articles = []
        for entry in feed.entries[:8]:
            raw_title = entry.title.strip()
            # Clean Google News "Title - Source" suffix if present
            if source_name == "Czech News" and " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title, pub = parts, parts
            else:
                title, pub = raw_title, source_name
            published = getattr(entry, "published", "")[:16]
            new_articles.append({
                "title": title,
                "link": entry.link.strip(),
                "meta": f"{pub} • {published}" if published else pub
            })
        if new_articles:
            data["news"] = new_articles
            print(f"Loaded {len(new_articles)} news items from {source_name}")
            break
    except Exception as e:
        print(f"News error ({source_name}):", e)

# 2. Fetch Obec Zelenec News with exact dates & title deduplication
try:
    vr = requests.get("https://zelenec.cz", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(vr.text, "html.parser")
    new_village = []
    seen_titles = set()

    container = soup.find("main") or soup
    skip_words = {
        "přeskočit", "zastupitelstvo", "výbory", "veřejné zakázky", "hospodaření",
        "vyhlášky", "povinně", "mstětice", "kontakty", "úřední deska", "aktuality",
        "kalendář", "fotogalerie", "ohlášení nedostatků"
    }

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
            # Look inside parent card/container for a Czech date (e.g. 24. 10. 2026)
            date_str = "Obec Zeleneč"
            parent = a.find_parent(["article", "li", "div"])
            for _ in range(3):
                if not parent:
                    break
                m = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", parent.get_text(" ", strip=True))
                if m:
                    date_str = m.group(1)
                    break
                parent = parent.parent

            # Strip date if it was inside the link text itself
            clean_title = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", title).strip()
            link = "https://zelenec.cz" + href

            if clean_title not in seen_titles and len(clean_title) > 10:
                seen_titles.add(clean_title)
                new_village.append({
                    "title": clean_title,
                    "link": link,
                    "date": date_str
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
