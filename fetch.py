import json, re, requests, feedparser
from bs4 import BeautifulSoup

data = {"trains": [], "village": [], "news": [], "weather": {}}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

# 1. Fetch Live Zelenec Trains from Sprava zeleznic Station Board
try:
    tr = requests.get("https://provoz.spravazeleznic.cz/tabule/Pages/StationTable.aspx?Key=5111", headers=HEADERS, timeout=15)
    if tr.status_code == 200:
        soup = BeautifulSoup(tr.text, "html.parser")
        for row in soup.select("table tr"):
            cols = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            # Columns: [0]=Pravidelny (HH:MM), [1]=Aktualni (HH:MM or empty), [3]=Vlak, [4]=Linka, [6]=Cil
            if len(cols) >= 7 and re.match(r"^\d{1,2}:\d{2}$", cols):
                sched = cols
                actual = cols if re.match(r"^\d{1,2}:\d{2}$", cols) else ""
                line = cols or cols
                dest = cols
                # Calculate delay in minutes if actual time differs from scheduled
                delay_min = 0
                if actual and actual != sched:
                    sh, sm = map(int, sched.split(":"))
                    ah, am = map(int, actual.split(":"))
                    delay_min = (ah * 60 + am) - (sh * 60 + sm)
                    if delay_min < -720:
                        delay_min += 1440
                data["trains"].append({
                    "time": actual or sched,
                    "sched": sched,
                    "train": f"{line} ({cols})".strip(),
                    "dest": dest,
                    "delay": max(0, delay_min)
                })
                if len(data["trains"]) >= 8:
                    break
except Exception as e:
    print("Trains fetch error:", e)

# 2. Fetch Zelenec Village News
try:
    vr = requests.get("https://www.zelenec.cz/aktuality", headers=HEADERS, timeout=15)
    if vr.status_code == 200:
        soup = BeautifulSoup(vr.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/aktuality/" in href and len(href) > 15 and "page=" not in href:
                title = " ".join(a.get_text().split())
                # Strip leading date if embedded in link text (e.g. "05. 11. 2026 Title")
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

# 4. Fetch Weather Backup (Zelenec & Prague)
for key, lat, lon in [("zelenec", 50.130, 14.666), ("prague", 50.075, 14.437)]:
    try:
        wr = requests.get(
            f"https://open-meteo.com{lat}&longitude={lon}&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min&timezone=Europe%2FPrague&forecast_days=1",
            timeout=10
        )
        if wr.status_code == 200:
            wj = wr.json()
            data["weather"][key] = {
                "temp": round(wj["current"]["temperature_2m"]),
                "code": wj["current"]["weather_code"],
                "max": round(wj["daily"]["temperature_2m_max"]),
                "min": round(wj["daily"]["temperature_2m_min"])
            }
    except Exception as e:
        print(f"Weather fetch error ({key}):", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> trains: {len(data['trains'])}, village: {len(data['village'])}, news: {len(data['news'])}, weather: {list(data['weather'].keys())}")
