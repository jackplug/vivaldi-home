import json, re, requests, feedparser
from bs4 import BeautifulSoup

data = {"trains": [], "village": [], "news": [], "weather": {}, "updated": ""}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

from datetime import datetime
data["updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# 1. Fetch Live Zelenec Trains from Sprava zeleznic Station Board (mapped by header name)
try:
    tr = requests.get("https://spravazeleznic.cz", headers=HEADERS, timeout=15)
    print("SZ Trains HTTP:", tr.status_code)
    if tr.status_code == 200:
        soup = BeautifulSoup(tr.text, "html.parser")
        table = soup.find("table")
        if table:
            headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
            for row in table.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
                if not cells or len(cells) < 5:
                    continue
                row_map = dict(zip(headers, cells)) if len(headers) == len(cells) else {}
                sched = row_map.get("Pravidelný", "")
                actual = row_map.get("Aktuální", "")
                train_name = row_map.get("Vlak", "")
                line = row_map.get("Linka", "")
                dest = row_map.get("Cíl", "")

                # Fallback if header count differs due to colspan
                if not sched:
                    times = [c for c in cells if re.match(r"^\d{1,2}:\d{2}$", c)]
                    if not times:
                        continue
                    sched = times.pop(0)
                    actual = times.pop(0) if times and times != sched else ""
                    non_times = [c for c in cells if c and c != "–" and not re.match(r"^\d{1,2}:\d{2}$", c)]
                    train_name = non_times.pop(0) if non_times else ""
                    line = non_times.pop(0) if non_times and len(non_times) <= 5 else ""
                    dest = non_times.pop(0) if non_times else ""

                if not re.match(r"^\d{1,2}:\d{2}$", sched):
                    continue

                delay_min = 0
                if actual and re.match(r"^\d{1,2}:\d{2}$", actual) and actual != sched:
                    sh, sm = map(int, sched.split(":"))
                    ah, am = map(int, actual.split(":"))
                    delay_min = (ah * 60 + am) - (sh * 60 + sm)
                    if delay_min < -720:
                        delay_min += 1440

                label = f"{line} • {train_name}".strip(" •") if line and line != "–" else train_name
                data["trains"].append({
                    "time": actual or sched,
                    "sched": sched,
                    "train": label,
                    "dest": dest,
                    "delay": max(0, delay_min)
                })
                if len(data["trains"]) >= 8:
                    break
except Exception as e:
    print("Trains fetch error:", e)

# 2. Fetch Zelenec Village News
try:
    vr = requests.get("https://zelenec.cz", headers=HEADERS, timeout=15)
    print("Zelenec HTTP:", vr.status_code)
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/aktuality/" in href and len(href) > 15 and "page=" not in href:
                title = " ".join(a.get_text().split())
                date_match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", title)
                date_str = date_match.group(1) if date_match else "Obec Zeleneč"
                clean_title = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", title).strip()
                link = href if href.startswith("http") else "https://www.zelenec.cz" + href
                if len(clean_title) > 8 and link not in seen:
                    seen.add(link)
                    data["village"].append({"title": clean_title, "link": link, "date": date_str})
                    if len(data["village"]) >= 6:
                        break
except Exception as e:
    print("Village fetch error:", e)

# 3. Fetch English Czech News
for source_name, url in [("Radio Prague", "https://radio.cz"), ("Expats.cz", "https://expats.cz")]:
    try:
        nr = requests.get(url, headers=HEADERS, timeout=15)
        print(f"News ({source_name}) HTTP:", nr.status_code)
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

# 4. Fetch Weather (Zelenec & Prague)
for key, lat, lon in [("zelenec", 50.130, 14.666), ("prague", 50.075, 14.437)]:
    try:
        wr = requests.get(
            f"https://open-meteo.com{lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=Europe%2FPrague",
            timeout=10
        )
        print(f"Weather ({key}) HTTP:", wr.status_code)
        if wr.status_code == 200:
            cur = wr.json().get("current", {})
            data["weather"][key] = {
                "temp": round(cur.get("temperature_2m", 0)),
                "feels": round(cur.get("apparent_temperature", 0)),
                "code": cur.get("weather_code", 0),
                "wind": round(cur.get("wind_speed_10m", 0))
            }
    except Exception as e:
        print(f"Weather fetch error ({key}):", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> trains: {len(data['trains'])}, village: {len(data['village'])}, news: {len(data['news'])}, weather: {list(data['weather'].keys())}")
