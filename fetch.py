import json, re, requests, feedparser
from bs4 import BeautifulSoup

data = {"trains": [], "village": [], "news": []}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

# 1. Fetch Live Zelenec Trains from Sprava zeleznic Station Board
try:
    tr = requests.get("https://spravazeleznic.cz", headers=HEADERS, timeout=15)
    print("SZ Trains HTTP:", tr.status_code)
    if tr.status_code == 200:
        soup = BeautifulSoup(tr.text, "html.parser")
        for row in soup.select("table tr"):
            cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            # Departure rows typically contain time (HH:MM), train ID, destination, and optional delay
            if len(cols) >= 3 and re.match(r"^\d{1,2}:\d{2}$", cols):
                time_str = cols
                train_name = cols
                dest = cols
                delay = cols[-1] if len(cols) > 3 and any(char.isdigit() for char in cols[-1]) else ""
                data["trains"].append({
                    "time": time_str,
                    "train": train_name,
                    "dest": dest,
                    "delay": delay
                })
                if len(data["trains"]) >= 8:
                    break
except Exception as e:
    print("Trains fetch error:", e)

# 2. Fetch Zelenec Village News with dates
try:
    vr = requests.get("https://zelenec.cz", headers=HEADERS, timeout=15)
    print("Zelenec HTTP:", vr.status_code)
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/aktuality/" in href and href.rstrip("/") != "/aktuality" and "page=" not in href:
                title = " ".join(a.get_text().split())
                link = href if href.startswith("http") else "https://zelenec.cz" + href
                if len(title) > 10 and link not in seen:
                    seen.add(link)
                    # Try grabbing nearby date or snippet from parent container
                    parent_text = " ".join(a.parent.get_text().split()) if a.parent else ""
                    date_match = re.search(r"\d{1,2}\.\s*\d{1,2}\.\s*\d{4}", parent_text)
                    date_str = date_match.group(0) if date_match else "Obec Zeleneč"
                    data["village"].append({"title": title, "link": link, "date": date_str})
                    if len(data["village"]) >= 6:
                        break
except Exception as e:
    print("Village fetch error:", e)

# 3. Fetch English Czech News with summaries & timestamps
rss_urls = [
    ("Radio Prague", "https://radio.cz"),
    ("Expats.cz", "https://expats.cz")
]
for source_name, url in rss_urls:
    try:
        nr = requests.get(url, headers=HEADERS, timeout=15)
        if nr.status_code == 200:
            feed = feedparser.parse(nr.text)
            for entry in feed.entries[:7]:
                raw_summary = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").get_text(" ", strip=True)
                summary = (raw_summary[:115] + "...") if len(raw_summary) > 115 else raw_summary
                published = getattr(entry, "published", "")[:16]
                data["news"].append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": summary,
                    "meta": f"{source_name} • {published}" if published else source_name
                })
            if data["news"]:
                break
    except Exception as e:
        print(f"News fetch error ({url}):", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> trains: {len(data['trains'])}, village: {len(data['village'])}, news: {len(data['news'])}")
