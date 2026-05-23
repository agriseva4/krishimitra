import logging, httpx
from app.config import OPENWEATHER_API_KEY, DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY

log = logging.getLogger(__name__)
TO = httpx.Timeout(10.0, connect=5.0)
BASE = "https://api.openweathermap.org/data/2.5"

async def get_weather(lat=None, lon=None, city=None) -> str:
    lat = lat or DEFAULT_LAT
    lon = lon or DEFAULT_LON
    city = city or DEFAULT_CITY
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "PASTE_HERE":
        return "❌ Weather key nahi. OPENWEATHER_API_KEY add kara."
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            curr = await c.get(f"{BASE}/weather", params={"lat":lat,"lon":lon,"appid":OPENWEATHER_API_KEY,"units":"metric"})
            fore = await c.get(f"{BASE}/forecast", params={"lat":lat,"lon":lon,"appid":OPENWEATHER_API_KEY,"units":"metric","cnt":6})
        if curr.status_code != 200:
            return "❌ Havaman data milala nahi. Parat prayatna kara."
        return _fmt(curr.json(), fore.json() if fore.status_code == 200 else None, city)
    except Exception as e:
        log.error(f"weather: {e}")
        return "❌ Havaman seva unavailable. Parat prayatna kara. 🙏"

def _fmt(c, f, city):
    try:
        temp, feels = c["main"]["temp"], c["main"]["feels_like"]
        humid, wind = c["main"]["humidity"], c["wind"]["speed"]
        desc = c["weather"][0]["description"].capitalize()
        rain = c.get("rain", {}).get("1h", 0)
        msg = (f"{_e(c['weather'][0]['id'])} *{city} — Aajche Havaman*\n\n"
               f"🌡️ Tapman: *{temp:.0f}°C* (Janvat: {feels:.0f}°C)\n"
               f"💧 Ardrata: *{humid}%*\n💨 Vaara: {wind:.1f} m/s\n🌥️ {desc}")
        if rain > 0: msg += f"\n🌧️ Paus: {rain:.1f}mm"
        tips = _tips(temp, humid, rain, wind)
        if tips: msg += f"\n\n🌾 *Shetkari Salla:*\n{tips}"
        if f and f.get("list"):
            msg += "\n\n📅 *Pudhe 24 Taas:*"
            for item in f["list"][:4]:
                t, tp = item["dt_txt"][11:16], item["main"]["temp"]
                d = item["weather"][0]["description"]
                r = item.get("rain", {}).get("3h", 0)
                msg += f"\n• {t}: {tp:.0f}°C — {d}" + (f" 🌧️{r:.0f}mm" if r > 0 else "")
        return msg + "\n\n_Source: OpenWeatherMap_"
    except Exception as e:
        log.error(f"weather fmt: {e}")
        return "❌ Havaman format error."

def _e(w):
    if w < 300: return "⛈️"
    if w < 400: return "🌦️"
    if w < 600: return "🌧️"
    if w < 700: return "❄️"
    if w < 800: return "🌫️"
    if w == 800: return "☀️"
    return "⛅"

def _tips(temp, humid, rain, wind):
    t = []
    if rain > 10: t.append("• Jaas paus — aaj spray karu naka")
    if humid > 80: t.append("• Jaas ardrata — fungal rogachi shakyata")
    if temp > 38: t.append("• Jaas una — doparee paani dya")
    if wind > 8: t.append("• Jaas vaara — spray karu naka")
    if temp < 15: t.append("• Thand — Tomato la protect kara")
    return "\n".join(t)
