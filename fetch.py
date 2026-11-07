import json, requests, feedparser
from bs4 import BeautifulSoup

data = {"village": [], "news": []}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

# 1. Fetch Zelenec Village News
try:
    vr = requests.get("https://www.zelenec.cz/aktuality", headers=HEADERS, timeout=15)
    print(f"Zelenec HTTP {vr.status_code}, length: {len(vr.text)}")
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        # Look for any link pointing to an article ID under /aktuality/
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/aktuality/" in href and href.rstrip("/") != "/aktuality" and "page=" not in href:
                title = " ".join(a.get_text().split())
                link = href if href.startswith("http") else "https://www.zelenec.cz" + href
                if len(title) > 10 and link not in seen:
                    seen.add(link)
                    data["village"].append({"title": title, "link": link})
                    if len(data["village"]) >= 6:
                        break
except Exception as e:
    print("Village fetch error:", e)

# 2. Fetch English Czech News (Radio Prague International + Expats.cz fallback)
rss_urls = [
    "https://english.radio.cz/rcz-rss/en",
    "https://expats.cz"
]
for url in rss_urls:
    try:
        nr = requests.get(url, headers=HEADERS, timeout=15)
        print(f"RSS {url} -> HTTP {nr.status_code}, length: {len(nr.text)}")
        if nr.status_code == 200:
            feed = feedparser.parse(nr.text)
            for entry in feed.entries[:8]:
                data["news"].append({"title": entry.title, "link": entry.link})
            if data["news"]:
                break
    except Exception as e:
        print(f"News fetch error ({url}):", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved data.json -> village: {len(data['village'])}, news: {len(data['news'])}")
