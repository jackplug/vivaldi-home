// 0. Clock & Random Nature Wallpaper (Forests, Mountains, Coastlines)
const NATURE_IDS = [
  10,   // Misty pine forest
  11,   // Forest valley & river
  13,   // Rocky ocean coast
  14,   // Coastal cliffs & sea
  15,   // Forest waterfall
  16,   // Calm misty sea horizon
  17,   // Green woodland path
  28,   // Deep evergreen forest
  29,   // Snow-capped mountain peaks
  37,   // Moody coastal shoreline
  54,   // Mountain ridge & clouds
  57,   // Alpine peaks at dusk
  70,   // Sunlight through forest trees
  110,  // Golden field & distant hills
  124,  // Calm ocean & rocky shore
  142   // Rolling mountain range
];

function applyWallpaper(forceRandom = false) {
  const savedBg = !forceRandom ? localStorage.getItem("custom_bg") : null;
  if (savedBg) {
    document.body.style.backgroundImage = `url("${savedBg}")`;
    return;
  }
  const idx = Math.floor(Math.random() * NATURE_IDS.length);
  const randomId = NATURE_IDS.at(idx);
  const host = "picsum" + ".photos";
  const bgUrl = "https://" + host + "/id/" + randomId + "/2000/1200";
  document.body.style.backgroundImage = `url("${bgUrl}")`;
}
applyWallpaper();

function changeWallpaper() {
  const current = localStorage.getItem("custom_bg") || "";
  const url = prompt("Paste a custom image URL (or leave blank for automatic random nature photos):", current);
  if (url === null) return;
  if (url.trim()) {
    localStorage.setItem("custom_bg", url.trim());
    applyWallpaper();
  } else {
    localStorage.removeItem("custom_bg");
    applyWallpaper(true);
  }
}

function updateClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  document.getElementById("clock-date").textContent = now.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
}
updateClock();
setInterval(updateClock, 15000);

// 1. Live Weather (Zeleneč & Prague 5-day forecast with inline SVG icons)
const GOLEMIO_URL = ["https:/", "api.golemio.cz", "v2", "pid", "departureboards"].join("/");

function getWeatherIcon(code) {
  const sun = `<circle cx="12" cy="12" r="5" fill="#fbbf24"/><path stroke="#fbbf24" stroke-width="2" stroke-linecap="round" d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41"/>`;
  const cloud = `<path fill="#94a3b8" d="M17.5 19H9a5 5 0 1 1 .9-9.9 6 6 0 0 1 11.6 2.4A4.5 4.5 0 0 1 17.5 19Z"/>`;
  const partly = `<circle cx="9" cy="9" r="4" fill="#fbbf24"/><path fill="#cbd5e1" d="M17.5 19H10a4.5 4.5 0 1 1 .8-8.9 5.5 5.5 0 0 1 10.7 2.2A4 4 0 0 1 17.5 19Z"/>`;
  const fog = `<path fill="#64748b" d="M17.5 14H9a4.5 4.5 0 1 1 .8-8.9 5.5 5.5 0 0 1 10.7 2.2A4 4 0 0 1 17.5 14Z"/><path stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" d="M4 17h16M6 20.5h12"/>`;
  const rain = `${cloud}<path stroke="#60a5fa" stroke-width="2" stroke-linecap="round" d="M9 20l-1 2m4-2l-1 2m4-2l-1 2"/>`;
  const snow = `${cloud}<circle cx="9" cy="21" r="1.2" fill="#e0f2fe"/><circle cx="13" cy="21" r="1.2" fill="#e0f2fe"/><circle cx="17" cy="21" r="1.2" fill="#e0f2fe"/>`;
  const storm = `${cloud}<path fill="#fbbf24" d="M13 13l-3 5h3l-1 4 4-6h-3l1-3z"/>`;

  let svg = partly;
  if (code === 0) svg = sun;
  else if (code === 1 || code === 2) svg = partly;
  else if (code === 3) svg = cloud;
  else if (code === 45 || code === 48) svg = fog;
  else if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)) svg = rain;
  else if ((code >= 71 && code <= 77) || code === 85 || code === 86) svg = snow;
  else if (code >= 95) svg = storm;

  return `<svg viewBox="0 0 24 24" width="20" height="20" style="vertical-align:middle; display:inline-block;">${svg}</svg>`;
}

async function getWeather(city, lat, lon) {
  const host = "api." + "open-meteo" + ".com";
  const qs = "latitude=" + lat + "&longitude=" + lon + "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FPrague&forecast_days=5";
  const res = await fetch("https://" + host + "/v1/forecast?" + qs);
  const d = await res.json();
  const c = d.current;
  const daily = d.daily;

  let forecastRows = "";
  for (let i = 0; i < daily.time.length; i++) {
    const dateObj = new Date(daily.time.at(i) + "T12:00:00");
    const dayName = i === 0 ? "Today" : dateObj.toLocaleDateString("en-GB", { weekday: "short" });
    const icon = getWeatherIcon(daily.weather_code.at(i));
    const hi = Math.round(daily.temperature_2m_max.at(i));
    const lo = Math.round(daily.temperature_2m_min.at(i));
    forecastRows += `<div class="forecast-row"><span class="forecast-day">${dayName}</span><span class="forecast-icon">${icon}</span><span class="forecast-temps"><strong>${hi}°</strong> <span class="temp-low">/ ${lo}°</span></span></div>`;
  }

  return `<div class="weather-box"><div class="weather-city">${city}</div><div class="weather-temp">${Math.round(c.temperature_2m)}°C</div><div class="weather-sub">${getWeatherIcon(c.weather_code)} Feels ${Math.round(c.apparent_temperature)}° • ${Math.round(c.wind_speed_10m)} km/h</div>${forecastRows}</div>`;
}

Promise.all([
  getWeather("Zeleneč", 50.130, 14.666),
  getWeather("Prague", 50.075, 14.437)
]).then(([zel, prg]) => {
  document.getElementById("weather").innerHTML = zel + prg;
}).catch(err => {
  document.getElementById("weather").innerHTML = `<div class="weather-box">Weather error: ${err.message}</div>`;
});

// 2. Live Zeleneč Trains
function setGolemioKey() {
  const k = prompt("Paste your Golemio API Key (saved only in Vivaldi):");
  if (k && k.trim()) {
    localStorage.setItem("golemio_key", k.trim());
    loadTrains();
  }
}

function loadTrains() {
  const key = localStorage.getItem("golemio_key");
  if (!key) {
    document.getElementById("trains").innerHTML = `<p class="muted-msg">Click <strong>API Key</strong> above to connect live Golemio train times.</p>`;
    return;
  }
  const u = new URL(GOLEMIO_URL);
  u.searchParams.set("names", "Zeleneč");
  u.searchParams.set("minutesAfter", "120");
  u.searchParams.set("limit", "8");

  fetch(u.toString(), { headers: { "X-Access-Token": key } })
    .then(r => r.ok ? r.json() : Promise.reject("HTTP " + r.status))
    .then(d => {
      document.getElementById("trains").innerHTML = (d.departures || []).map(t => {
        const line = t.route?.short_name || "Train";
        const dest = t.trip?.headsign || "";
        const time = (t.departure_timestamp?.predicted || "").slice(11, 16);
        const delay = t.delay?.minutes || 0;
        return `<div class="train-row"><div class="train-time">${time}</div><div class="train-info"><div class="train-dest">${dest}</div><div class="train-num">Line ${line}</div></div><div class="${delay > 0 ? 'badge-delay' : 'badge-ok'}">${delay > 0 ? '+' + delay + ' min' : 'On time'}</div></div>`;
      }).join("") || "<p class='muted-msg'>No trains in next 2 hours.</p>";
    })
    .catch(err => {
      document.getElementById("trains").innerHTML = `<p class="muted-msg">Train feed error (${err}).</p>`;
    });
}
loadTrains();

// 3. Village, Facebook & Czech News
async function translateCzToEn(text) {
  if (!text) return "";
  try {
    const host = "translate." + "googleapis" + ".com";
    const u = new URL("https://" + host + "/translate_a/single");
    u.searchParams.set("client", "gtx");
    u.searchParams.set("sl", "cs");
    u.searchParams.set("tl", "en");
    u.searchParams.set("dt", "t");
    u.searchParams.set("q", text);
    const r = await fetch(u.toString());
    const d = await r.json();
    return (d.at(0) || []).map(c => c.at(0) || "").join("").trim() || text;
  } catch {
    return text;
  }
}

const dataUrl = new URL("./data.json", window.location.href);
dataUrl.searchParams.set("t", Date.now());
fetch(dataUrl.toString())
  .then(r => r.json())
  .then(async d => {
    document.getElementById("news").innerHTML = (d.news || []).map(n => `
      <div class="news-item">
        <div class="news-meta">${n.meta || "Czech News"}</div>
        <a href="${n.link}" target="_blank">${n.title}</a>
      </div>
    `).join("") || "<p class='muted-msg'>No Czech news found.</p>";

    const villageItems = await Promise.all((d.village || []).map(async v => {
      const enTitle = await translateCzToEn(v.title);
      const enSummary = v.summary ? await translateCzToEn(v.summary) : "";
      return `
        <div class="news-item">
          <div class="news-meta">${v.date || "Obec Zeleneč"}</div>
          <a href="${v.link}" target="_blank">${enTitle}</a>
          ${enSummary ? `<div class="news-summary">${enSummary}</div>` : ""}
          ${enTitle !== v.title ? `<div class="news-cz">${v.title}</div>` : ""}
        </div>`;
    }));

    const fbItems = await Promise.all((d.facebook || []).map(async fb => {
      const enText = await translateCzToEn(fb.text);
      return `
        <div class="news-item">
          <div class="news-meta">${fb.date}</div>
          <a href="${fb.link}" target="_blank">${enText}</a>
          ${enText !== fb.text ? `<div class="news-cz">${fb.text}</div>` : ""}
        </div>`;
    }));

    document.getElementById("village-web").innerHTML = villageItems.join("") || "<p class='muted-msg'>No website news found.</p>";
    document.getElementById("village-fb").innerHTML = fbItems.join("") || "<p class='muted-msg'>No Facebook posts found.</p>";
  });
