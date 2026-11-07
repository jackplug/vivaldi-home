import os, json, requests, feedparser
from bs4 import BeautifulSoup

data = {"trains": [], "village": [], "news": []}

# 1. Fetch Zelenec Trains via Golemio
headers = {"X-Access-Token": os.environ.get("GOLEMIO_KEY", "")}
r = requests.get("https://golemio.cz", headers=headers)
if r.ok:
    for dep in r.json().get("departures", []):
        data["trains"].append({
            "line": dep["route"]["short_name"],
            "dest": dep["trip"]["headsign"],
            "time": dep["departure_timestamp"]["predicted"][11:16],
            "delay": dep["delay"]["minutes"]
        })

# 2. Fetch Zelenec Village News
vr = requests.get("https://zelenec.cz", timeout=10)
if vr.ok:
    soup = BeautifulSoup(vr.text, "html.parser")
    for a in soup.select("a[href*='/aktuality/']")[:6]:
        title = a.get_text(strip=True)
        if len(title) > 10:
            link = a["href"] if a["href"].startswith("http") else "https://zelenec.cz" + a["href"]
            data["village"].append({"title": title, "link": link})

# 3. Fetch English Czech News (Radio Prague)
feed = feedparser.parse("https://radio.cz")
for entry in feed.entries[:8]:
    data["news"].append({"title": entry.title, "link": entry.link})

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
