import json, os, re, requests, feedparser
from datetime import datetime
from bs4 import BeautifulSoup

existing = {"village": [], "facebook": [], "news": []}
if os.path.exists("data.json"):
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

data = {
    "village": existing.get("village", []),
    "facebook": existing.get("facebook", []),
    "news": existing.get("news", []),
    "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8"
}

# 1. Fetch English Czech News (Radio Prague)
rp_url = "https://" + "english.radio.cz" + "/rcz-rss/en"
try:
    feed = feedparser.parse(rp_url)
    new_articles = []
    for entry in feed.entries[:8]:
        published = getattr(entry, "published", "")[:16]
        new_articles.append({
            "title": entry.title.strip(),
            "link": entry.link.strip(),
            "meta": f"Radio Prague • {published}" if published else "Radio Prague"
        })
    if new_articles:
        data["news"] = new_articles
except Exception as e:
    print("News error:", e)

# 2. Fetch Obec Zelenec Website News + Perex
try:
    vr_url = "https://" + "www.zelenec.cz" + "/aktuality"
    vr = requests.get(vr_url, headers=HEADERS, timeout=15)
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
            link = "https://" + "www.zelenec.cz" + href

            if clean_cz not in seen_titles and len(clean_cz) > 10:
                seen_titles.add(clean_cz)
                new_village.append({
                    "title": clean_cz,
                    "summary": perex_cz,
                    "link": link,
                    "date": date_str
                })
                if len(new_village) >= 4:
                    break

    if new_village:
        data["village"] = new_village
except Exception as e:
    print("Village error:", e)

# 3. Fetch Top 3 Obec Zelenec Facebook Posts via FetchRSS
fb_url = "https://" + "fetchrss.com" + "/feed/1xPpDE2yD6CY1xPp53BvBGMU.rss"
try:
    fb_feed = feedparser.parse(fb_url)
    new_fb = []
    for entry in fb_feed.entries[:3]:
        raw_text = BeautifulSoup(getattr(entry, "summary", entry.title), "html.parser").get_text(" ", strip=True)
        raw_text = raw_text.replace("(Feed generated with FetchRSS)", "").strip()
        snippet = (raw_text[:145] + "...") if len(raw_text) > 145 else raw_text
        published = getattr(entry, "published", "")[:16]
        new_fb.append({
            "text": snippet,
            "link": entry.link.strip(),
            "date": published or "Facebook"
        })
    if new_fb:
        data["facebook"] = new_fb
except Exception as e:
    print("Facebook RSS error:", e)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Saved -> village: {len(data['village'])}, fb: {len(data['facebook'])}, news: {len(data['news'])}")
