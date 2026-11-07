import json, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

data = {
    "trains": [],
    "village": [],
    "news": [],
    "weather": {},
    "errors": [],
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

HEADERS = {
    "User-Agent": "VivaldiHomeDashboard/1.0 (https://github.com)",
    "Accept": "*/*"
}

# 1. Weather via Norwegian Meteorological Institute (met.no - official, accurate, allows GitHub Actions)
symbol_map = {
    "clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3,
    "fog": 45, "lightrain": 51, "rain": 61, "heavyrain": 61,
    "snow": 71, "lightsnow": 71, "rainshowers": 80, "thunderstorm": 95
}
for key, lat, lon in [("zelenec", 50.130, 14.666), ("prague", 50.075, 14.437)]:
    try:
        wr = requests.get(
            f"https://met.no{lat}&lon={lon}",
            headers=HEADERS,
            timeout=15
        )
        wr.raise_for_status()
        ts = wr.json()["properties"]["timeseries"]
        details = ts["data"]["instant"]["details"]
        sym = ts["data"].get("next_1_hours", {}).get("summary", {}).get("symbol_code", "cloudy").split("_")
        data["weather"][key] = {
            "temp": round(details.get("air_temperature", 0)),
            "feels": round(details.get("air_temperature", 0)),
            "code": symbol_map.get(sym, 3),
            "wind": round(details.get("wind_speed", 0) * 3.6)  # m/s -> km/h
        }
    except Exception as e:
        data["errors"].append(f"Weather ({key}): {e}")

# 2. English Czech News (Prague Morning RSS + Radio Prague fallback)
for source_name, url in [
    ("Prague Morning", "https://praguemorning.cz"),
    ("Radio Prague", "https://radio.cz")
]:
    try:
        nr = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if nr.status_code == 200 and len(nr.text) > 200:
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

# 3. Zelenec Train Departures (IDnes Jizdni rady static HTML board)
try:
    tr = requests.get(
        "https://idnes.cz",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"},
        timeout=15
    )
    soup = BeautifulSoup(tr.text, "html.parser")
    for row in soup.select("table tr"):
        cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        times = [c for c in cols if re.match(r"^\d{1,2}:\d{2}$", c)]
        if times and len(cols) >= 3:
            time_str = times.pop(0)
            non_times = [c for c in cols if c and not re.match(r"^\d{1,2}:\d{2}$", c)]
            train_name = non_times.pop(0) if non_times else "Train"
            dest = non_times.pop(0) if non_times else ""
            delay_match = re.search(r"(\d+)\s*min", " ".join(cols))
            delay_min = int(delay_match.group(1)) if delay_match else 0
            data["trains"].append({
                "time": time_str,
                "train": train_name,
                "dest": dest,
                "delay": delay_min
            })
            if len(data["trains"]) >= 8:
                break
except Exception as e:
    data["errors"].append(f"Trains: {e}")

# 4. Zelenec Village News (matches /aktuality/aktuality/<id> links anywhere on page)
try:
    vr = requests.get("https://www.zelenec.cz/aktuality", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(vr.text, "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/aktuality/aktuality/" in href:
            text = " ".join(a.get_text().split())
            date_match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", text)
            date_str = date_match.group(1) if date_match else "Obec Zeleneč"
            clean_title = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", text).strip()
            link = href if href.startswith("http") else "https://www.zelenec.cz" + href
            if len(clean_title) > 5 and link not in seen:
                seen.add(link)
                data["village"].append({"title": clean_title, "link": link, "date": date_str})
                if len(data["village"]) >= 6:
                    break
except Exception as e:
    data["errors"].append(f"Village: {e}")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
