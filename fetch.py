import os, json, requests, feedparser
from bs4 import BeautifulSoup

data = {"trains": [], "village": [], "news": [], "debug": ""}

# 1. Fetch Zelenec Trains via Golemio
api_key = os.environ.get("GOLEMIO_KEY", "").strip()
if not api_key:
    data["debug"] = "Missing GOLEMIO_API_KEY secret"
else:
    headers = {
        "X-Access-Token": api_key,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; VivaldiHomeDashboard/1.0)"
    }
    url = "https://golemio.cz"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        content_type = r.headers.get("Content-Type", "")
        print(f"Golemio status: {r.status_code}, type: {content_type}, length: {len(r.text)}")
        
        if r.status_code == 200 and "application/json" in content_type:
            for dep in r.json().get("departures", []):
                data["trains"].append({
                    "line": dep.get("route", {}).get("short_name", "?"),
                    "dest": dep.get("trip", {}).get("headsign", ""),
                    "time": dep.get("departure_timestamp", {}).get("predicted", "")[11:16],
                    "delay": dep.get("delay", {}).get("minutes", 0)
                })
        else:
            snippet = r.text[:150].replace("\n", " ")
            print("Golemio non-JSON response preview:", snippet)
            data["debug"] = f"Golemio returned {r.status_code} ({content_type})"
    except Exception as e:
        print("Golemio error:", e)
        data["debug"] = str(e)

# 2. Fetch Zelenec Village News
try:
    vr = requests.get("https://zelenec.cz", timeout=15)
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        for a in soup.select("a[href*='/aktuality/']"):
            title = a.get_text(strip=True)
            link = a["href"] if a["href"].startswith("http") else "https://zelenec.cz" + a["href"]
            if len(title) > 10 and link not in seen:
                seen.add(link)
                data["village"].append({"title": title, "link": link})
                if len(data["village"]) >= 6:
                    break
except Exception as e:
    print("Village fetch error:", e)

# 3. Fetch English Czech News (Radio Prague)
try:
    feed = feedparser.parse("https://radio.cz")
    for entry in feed.entries[:8]:
        data["news"].append({"title": entry.title, "link": entry.link})
except Exception as e:
    print("News fetch error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Successfully wrote data.json")
