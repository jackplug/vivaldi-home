import json, os, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

existing = {"village": [], "news": []}
if os.path.exists("data.json"):
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

data = {
    "village": existing.get("village", []),
    "news": existing.get("news", []),
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

def translate_cs_to_en(text):
    if not text:
        return ""
    try:
        host = "translate." + "googleapis" + ".com"
        url = "https://" + host + "/translate_a/single"
        r = requests.get(
            url,
            params={"client": "gtx", "sl": "cs", "tl": "en", "dt": "t", "q": text},
            timeout=10
        )
        if r.status_code == 200:
            raw = r.json()
            if isinstance(raw, list) and len(raw) > 0 and isinstance(raw.pop(0), list):
                pass
            # Re-parse cleanly without mutating
            raw = r.json()
            sentences = raw[0] if isinstance(raw, list) and raw else []
            translated = "".join(s[0] for s in sentences if isinstance(s, list) and s and isinstance(s[0], str))
            if translated.strip():
                return translated.strip()
    except Exception as e:
        print("Translate error:", e)
    return text

# 1. Fetch English Czech News
rp_url = "https://" + "english.radio.cz" + "/rcz-rss/en"
gn_url = "https://" + "://google.com" + "/rss/search?q=Czechia+OR+Prague&hl=en-US&gl=US&ceid=US:en"

for source_name, url in [("Radio Prague", rp_url), ("Czech News", gn_url)]:
    try:
        feed = feedparser.parse(url)
        new_articles = []
        for entry in feed.entries[:8]:
            raw_title = entry.title.strip()
            if source_name == "Czech News" and " - " in raw_title:
                parts = raw_title.rsplit(" - ", 1)
                title, pub = parts[0], parts[1]
            else:
                title, pub = raw_title, source_name
            published = getattr(entry, "published", "")[:16]
            new_articles.append({
                "title": title,
                "link": entry.link.strip(),
                "meta": f"{pub} • {published}" if published else pub
            })
        if new_articles:
            data["news"] = new_articles
            break
    except Exception as e:
        print(f"News error ({source_name}):", e)

# 2. Fetch Obec Zelenec News + Perex + Translate Both to English
try:
    vr = requests.get("https://zelenec.cz", headers=HEADERS, timeout=15)
    soup = BeautifulSoup(vr.text, "html.parser")
    new_village = []
    seen_titles = set()

    container = soup.find("main") or soup
    skip_words = {
        "přeskočit", "zastupitelstvo", "výbory", "veřejné zakázky", "hospodaření",
        "vyhlášky", "povinně", "mstětice", "kontakty", "úřední deska", "aktuality",
        "kalendář", "fotogalerie", "ohlášení nedostatků", "život v zelenči"
    }

    for a in container.find_all("a", href=True):
        href = a["href"]
        title = " ".join(a.get_text().split())
        low = title.lower()
        if (
            href.startswith("/")
            and len(href) > 12
            and len(title) > 14
            and not any(w in low for w in skip_words)
            and "filter-" not in href
            and "page=" not in href
        ):
            date_str = "Obec Zeleneč"
            perex_cz = ""
            card = a.find_parent(["article", "li", "div"])
            for _ in range(3):
                if not card:
                    break
                card_text = " ".join(card.get_text(" ", strip=True).split())
                m = re.search(r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", card_text)
                if m:
                    date_str = m.group(1)
                    p_tag = card.find("p")
                    if p_tag:
                        perex_cz = " ".join(p_tag.get_text().split())
                    else:
                        remainder = card_text.replace(date_str, "").replace(title, "").strip()
                        remainder = re.sub(r"\s+\d+$", "", remainder).strip()
                        if 8 < len(remainder) < 220:
                            perex_cz = remainder
                    break
                card = card.parent

            clean_cz = re.sub(r"^\d{1,2}\.\s*\d{1,2}\.\s*\d{4}\s*", "", title).strip()
            if perex_cz == clean_cz:
                perex_cz = ""
            link = "https://zelenec.cz" + href

            if clean_cz not in seen_titles and len(clean_cz) > 10:
                seen_titles.add(clean_cz)
                en_title = translate_cs_to_en(clean_cz)
                en_perex = translate_cs_to_en(perex_cz) if perex_cz else ""
                new_village.append({
                    "title": en_title,
                    "cz": clean_cz,
                    "summary": en_perex,
                    "link": link,
                    "date": date_str
                })
                if len(new_village) >= 6:
                    break

    if new_village:
        data["village"] = new_village
except Exception as e:
    print("Village error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> village: {len(data['village'])}, news: {len(data['news'])}")
