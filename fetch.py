import json, re, urllib.request, xml.etree.ElementTree as ET
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

def get_url(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")

# 1. Weather (Open-Meteo)
for key, lat, lon in [("zelenec", 50.130, 14.666), ("prague", 50.075, 14.437)]:
    try:
        raw = get_url(f"https://open-meteo.com{lat}&longitude={lon}&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=Europe%2FPrague")
        cur = json.loads(raw).get("current", {})
        data["weather"][key] = {
            "temp": round(cur.get("temperature_2m", 0)),
            "feels": round(cur.get("apparent_temperature", 0)),
            "code": cur.get("weather_code", 0),
            "wind": round(cur.get("wind_speed_10m", 0))
        }
    except Exception as e:
        data["errors"].append(f"Weather ({key}): {e}")

# 2. English Czech News (Radio Prague XML)
try:
    xml_text = get_url("https://radio.cz")
    root = ET.fromstring(xml_text)
    for item in root.findall(".//item")[:7]:
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        desc = BeautifulSoup(item.findtext("description", ""), "html.parser").get_text(" ", strip=True)
        pub = item.findtext("pubDate", "")[:16]
        if title and link:
            data["news"].append({
                "title": title,
                "link": link,
                "summary": (desc[:115] + "...") if len(desc) > 115 else desc,
                "meta": f"Radio Prague • {pub}" if pub else "Radio Prague"
            })
except Exception as e:
    data["errors"].append(f"News: {e}")

# 3. Zelenec Trains (Sprava zeleznic)
try:
    html = get_url("https://spravazeleznic.cz")
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("table tr"):
        cells = [td.get_text(" ", strip=True) for td in row.find_all("td")]
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
except Exception as e:
    data["errors"].append(f"Trains: {e}")

# 4. Zelenec Village News
try:
    vhtml = get_url("https://zelenec.cz")
    soup = BeautifulSoup(vhtml, "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/aktuality/" in href and len(href) > 15 and "page=" not in href:
            title = " ".join(a.get_text().split())
            date_match = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", title)
            date_str = date_match.group(1) if date_match else "Obec Zeleneč"
            clean_title = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", title).strip()
            link = href if href.startswith("http") else "https://zelenec.cz" + href
            if len(clean_title) > 8 and link not in seen:
                seen.add(link)
                data["village"].append({"title": clean_title, "link": link, "date": date_str})
                if len(data["village"]) >= 6:
                    break
except Exception as e:
    data["errors"].append(f"Village: {e}")

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
