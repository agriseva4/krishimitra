import logging, httpx
from app.config import OPENWEATHER_API_KEY, DEFAULT_LAT, DEFAULT_LON, DEFAULT_CITY

log = logging.getLogger(__name__)
TO = httpx.Timeout(10.0, connect=5.0)
BASE = "https://api.openweathermap.org/data/2.5"

# OpenWeatherMap नेहमी इंग्रजीत description देतं (उदा. "light rain", "broken clouds") —
# farmer ला ते तसंच पाठवलं जायचं. आता condition-code (id) वरून मराठी शब्द वापरतो.
_WEATHER_MR = {
    range(200, 233): "मेघगर्जनेसह पाऊस",
    range(300, 322): "रिमझिम पाऊस",
    range(500, 505): "पाऊस",
    range(511, 512): "गोठणारा पाऊस",
    range(520, 532): "सरींचा पाऊस",
    range(600, 623): "बर्फवृष्टी",
    range(701, 702): "धुके",
    range(711, 712): "धूर",
    range(721, 722): "धुरकट वातावरण",
    range(731, 732): "वाळूचे वादळ",
    range(741, 742): "दाट धुके",
    range(751, 762): "वाळू/धूळमिश्रित वारा",
    range(762, 763): "ज्वालामुखी राख",
    range(771, 772): "वादळी वारा",
    range(781, 782): "चक्रीवादळ",
    range(800, 801): "स्वच्छ ऊन",
    range(801, 803): "अंशतः ढगाळ",
    range(803, 805): "ढगाळ वातावरण",
}

def _desc_mr(weather_id: int) -> str:
    for r, mr in _WEATHER_MR.items():
        if weather_id in r:
            return mr
    return "सर्वसाधारण हवामान"

async def get_weather(lat=None, lon=None, city=None) -> str:
    lat = lat or DEFAULT_LAT
    lon = lon or DEFAULT_LON
    city = city or DEFAULT_CITY
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "PASTE_HERE":
        return "❌ *हवामान सेवा उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा. 🙏"
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            curr = await c.get(f"{BASE}/weather", params={"lat":lat,"lon":lon,"appid":OPENWEATHER_API_KEY,"units":"metric"})
            fore = await c.get(f"{BASE}/forecast", params={"lat":lat,"lon":lon,"appid":OPENWEATHER_API_KEY,"units":"metric","cnt":6})
        if curr.status_code != 200:
            return "❌ *हवामान माहिती मिळाली नाही.*\nकृपया पुन्हा प्रयत्न करा. 🙏"
        return _fmt(curr.json(), fore.json() if fore.status_code == 200 else None, city)
    except Exception as e:
        log.error(f"weather: {e}")
        return "❌ *हवामान सेवा सध्या व्यस्त आहे.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"

def _fmt(c, f, city):
    try:
        temp, feels = c["main"]["temp"], c["main"]["feels_like"]
        humid, wind = c["main"]["humidity"], c["wind"]["speed"]
        weather_id = c["weather"][0]["id"]
        desc = _desc_mr(weather_id)
        rain = c.get("rain", {}).get("1h", 0)
        msg = (f"{_e(weather_id)} *{city} — आजचे हवामान*\n\n"
               f"🌡️ तापमान: *{temp:.0f}°C* (जाणवते: {feels:.0f}°C)\n"
               f"💧 आर्द्रता: *{humid}%*\n"
               f"💨 वारा: {wind:.1f} m/s\n"
               f"🌥️ {desc}")
        if rain > 0: msg += f"\n🌧️ पाऊस: {rain:.1f}mm"
        tips = _tips(temp, humid, rain, wind)
        if tips: msg += f"\n\n🌾 *शेतकरी सल्ला:*\n{tips}"
        if f and f.get("list"):
            msg += "\n\n📅 *पुढे २४ तास:*"
            for item in f["list"][:4]:
                t, tp = item["dt_txt"][11:16], item["main"]["temp"]
                d = _desc_mr(item["weather"][0]["id"])
                r = item.get("rain", {}).get("3h", 0)
                msg += f"\n• {t}: {tp:.0f}°C — {d}" + (f" 🌧️{r:.0f}mm" if r > 0 else "")
        return msg + "\n\n_स्रोत: OpenWeatherMap_"
    except Exception as e:
        log.error(f"weather fmt: {e}")
        return "❌ *हवामान माहिती दाखवताना अडचण आली.*"

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
    if rain > 10: t.append("• जास्त पाऊस — आज फवारणी करू नका")
    if humid > 80: t.append("• जास्त आर्द्रता — बुरशीजन्य रोगाची शक्यता")
    if temp > 38: t.append("• जास्त ऊन — दुपारी पाणी द्या")
    if wind > 8: t.append("• जास्त वारा — फवारणी करू नका")
    if temp < 15: t.append("• थंडी — टोमॅटोला संरक्षण द्या")
    return "\n".join(t)
