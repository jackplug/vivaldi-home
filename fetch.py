import json, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

data = {
    "trains": [],
    "village": [],
    "news": [],
    "weather": {},
    "errors": [],
    "debug": {},
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,cs;q=0.8",
    "Referer": "https://google.com"
}

# 1. Weather (Open-Meteo with explicit params dictionary so URL is always clean)
for key, lat, lon in [("zelenec", 50.130, 14.666), ("prague", 50.075, 14.437)]:
    try:
        wr = requests.get(
            "https://open-meteo.com",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "timezone": "Europe/Prague"
            },
            timeout=10
        )
        wr.raise_for_status()
        cur = wr.json().get("current", {})
        data["weather"][key] = {
            "temp": round(cur.get("temperature_2m", 0)),
            "feels": round(cur.get("apparent_temperature", 0)),
            "code": cur.get("weather_code", 0),
            "wind": round(cur.get("wind_speed_10m", 0))
        }
    except Exception as e:
        data["errors"].append(f"Weather ({key}): {e}")

# 2. English Czech News (Radio Prague + Expats.cz via requests)
for source_name, url in [
    ("Radio Prague", "https://radio.cz"),
    ("Expats.cz", "https://expats.cz")
]:
    try:
        nr = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
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
        else:
            data["errors"].append(f"News ({source_name}): HTTP {nr.status_code}")
    except Exception as e:
        data["errors"].append(f"News ({source_name}): {e}")

# 3. Zelenec Trains (Sprava zeleznic) + sample rows in debug
try:
    tr = requests.get("https://spravazeleznic.cz", headers=BROWSER_HEADERS, timeout=15)
    soup = BeautifulSoup(tr.text, "html.parser")
    sample_rows = []
    for row in soup.select("tr"):
        cells = [td.get_text(" ", strip=True) for td in row.find_all(["td", "th"]) if td.get_text(strip=True)]
        if cells:
            sample_rows.append(cells)
        times = [c for c in cells if re.match(r"^\d{1,2}:\d{2}$", c)]
        non_times = [c for c in cells if c and c != "–" and not re.match(r"^\d{1,2}:\d{2}$", c)]
        if times and len(non_times) >= 2:
            sched = times.pop(0)
            actual = times.pop(0) if times and times != sched else ""
            train_name = non_times.pop(0)
            dest = non_times.pop()
            delay_min = 0
            if actual:
                sh, sm = map(int, sched.split(":"))
                ah, am = map(int, actual.split(":"))
                delay_min = max(0, (ah * 60 + am) - (sh * 60 + sm))
            data["trains"].append({
                "time": actual or sched,
                "train": train_name,
                "dest": dest,
                "delay": delay_min
            })
            if len(data["trains"]) >= 8:
                break
    data["debug"]["sz_rows"] = sample_rows[:5]
except Exception as e:
    data["errors"].append(f"Trains: {e}")

# 4. Zelenec Village News + sample links in debug
try:
    vr = requests.get("https://zelenec.cz", headers=BROWSER_HEADERS, timeout=15)
    soup = BeautifulSoup(vr.text, "html.parser")
    seen = set()
    sample_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = " ".join(a.get_text().split())
        if len(text) > 12:
            sample_links.append({"text": text[:60], "href": href})
        if "/aktuality/" in href and len(href) > 15 and "page=" not in href:
            date_match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", text)
            date_str = date_match.group(1) if date_match else "Obec Zeleneč"
            clean_title = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", text).strip()
            link = href if href.startswith("http") else "https://zelenec.cz" + href
            if len(clean_title) > 8 and link not in seen:
                seen.add(link)
                data["village"].append({"title": clean_title, "link": link, "date": date_str})
                if len(data["village"]) >= 6:
                    break
    data["debug"]["zelenec_links"] = sample_links[:8]
except Exception as e:
    data["errors"].append(f"Village: {e}")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
