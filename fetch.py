import json, requests, feedparser
from bs4 import BeautifulSoup

data = {"village": [], "news": []}
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

# 1. Fetch Zelenec Village News
try:
    vr = requests.get("https://zelenec.cz", headers=BROWSER_HEADERS, timeout=15)
    print("Zelenec status:", vr.status_code)
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        for a in soup.select("a[href*='/aktuality/aktuality/']"):
            title = " ".join(a.get_text().split())
            link = a["href"] if a["href"].startswith("http") else "https://zelenec.cz" + a["href"]
            if len(title) > 8 and link not in seen:
                seen.add(link)
                data["village"].append({"title": title, "link": link})
                if len(data["village"]) >= 6:
                    break
except Exception as e:
    print("Village fetch error:", e)

# 2. Fetch English Czech News (Radio Prague International)
try:
    nr = requests.get("https://radio.cz", headers=BROWSER_HEADERS, timeout=15)
    print("Radio Prague status:", nr.status_code)
    if nr.status_code == 200:
        feed = feedparser.parse(nr.text)
        for entry in feed.entries[:8]:
            data["news"].append({"title": entry.title, "link": entry.link})
except Exception as e:
    print("News fetch error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Done! Village items: {len(data['village'])}, News items: {len(data['news'])}")
