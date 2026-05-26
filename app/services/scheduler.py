import logging, asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)
_s = AsyncIOScheduler()

def start_scheduler():
    if _s.running: return
    _s.add_job(morning, CronTrigger(hour=7, minute=0), id="morning", replace_existing=True)
    _s.add_job(evening, CronTrigger(hour=18, minute=0), id="evening", replace_existing=True)
    _s.add_job(weekly, CronTrigger(day_of_week="mon", hour=8, minute=0), id="weekly", replace_existing=True)
    _s.add_job(weather_alert_check, CronTrigger(minute=0), id="weather_alert", replace_existing=True)
    _s.start()
    log.info("✅ Scheduler started: 7AM | 6PM | Monday | Hourly alert check")

async def weather_alert_check():
    try:
        from app.services.database import get_all_farmers
        from app.services.whatsapp import send_message
        import httpx
        from app.config import OPENWEATHER_API_KEY

        farmers = await get_all_farmers()
        if not farmers: return

        alerted_locations = set()

        for f in farmers:
            try:
                lat = f.get("lat", 18.5204)
                lon = f.get("lon", 73.8567)
                city = f.get("city", "Pune")
                loc_key = f"{round(lat,1)}_{round(lon,1)}"

                if loc_key in alerted_locations:
                    continue

                url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&cnt=3"

                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(url)
                    if r.status_code != 200:
                        continue
                    data = r.json()

                alert_msg = _check_danger(data, city)

                if alert_msg:
                    alerted_locations.add(loc_key)
                    for farmer in farmers:
                        floc = f"{round(farmer.get('lat',18.5204),1)}_{round(farmer.get('lon',73.8567),1)}"
                        if floc == loc_key:
                            await send_message(farmer["phone"], alert_msg)
                            await asyncio.sleep(0.5)

                await asyncio.sleep(0.3)

            except Exception as e:
                log.warning(f"Alert check {f.get('phone')}: {e}")

    except Exception as e:
        log.error(f"weather_alert_check: {e}")

def _check_danger(data: dict, city: str) -> str:
    try:
        forecasts = data.get("list", [])
        if not forecasts: return ""

        max_rain = 0
        max_wind = 0
        max_temp = 0
        thunderstorm = False
        heavy_rain = False
        strong_wind = False
        heat_wave = False

        for fc in forecasts[:3]:
            weather_main = fc.get("weather", [{}])[0].get("main", "").lower()
            weather_desc = fc.get("weather", [{}])[0].get("description", "").lower()
            wind_speed = fc.get("wind", {}).get("speed", 0)
            rain_1h = fc.get("rain", {}).get("1h", 0)
            rain_3h = fc.get("rain", {}).get("3h", 0)
            temp = fc.get("main", {}).get("temp", 0)

            rain_amount = max(rain_1h, rain_3h / 3)
            max_rain = max(max_rain, rain_amount)
            max_wind = max(max_wind, wind_speed)
            max_temp = max(max_temp, temp)

            if "thunderstorm" in weather_main or "thunderstorm" in weather_desc:
                thunderstorm = True
            if rain_amount > 7 or "heavy" in weather_desc:
                heavy_rain = True
            if wind_speed > 10:
                strong_wind = True
            if temp > 40:
                heat_wave = True

        if not any([thunderstorm, heavy_rain, strong_wind, heat_wave]):
            return ""

        now = datetime.now()
        t1 = f"{now.hour + 1}:{now.minute:02d}"
        t2 = f"{now.hour + 3}:{now.minute:02d}"

        if thunderstorm:
            icon = "⛈️"
        elif heavy_rain:
            icon = "🌧️"
        elif strong_wind:
            icon = "💨"
        else:
            icon = "🥵"

        msg = f"{icon} *KrishiMitra हवामान अलर्ट — {city}*\n\n"
        msg += f"शेतकरी मित्रा 🙏\n"

        situations = []
        if thunderstorm:
            situations.append("विजेसह जोरदार मेघगर्जना")
        if heavy_rain:
            situations.append(f"जोरदार पाऊस ({max_rain:.1f} mm)")
        if strong_wind:
            situations.append(f"जोरदार वारा ({max_wind:.0f} m/s)")
        if heat_wave:
            situations.append(f"उष्णतेची लाट ({max_temp:.0f}°C)")

        sit_text = " व ".join(situations)
        msg += f"तुमच्या भागात पुढील {t1} ते {t2} दरम्यान *{sit_text}* होण्याची शक्यता आहे.\n\n"

        msg += "*👉 तातडीने करा:*\n"

        if thunderstorm or heavy_rain:
            msg += "• ⚠️ फवारणी आत्ताच बंद करा\n"
            msg += "• ⚡ शेतातील विद्युत मोटर बंद ठेवा\n"
            msg += "• 🐄 जनावरांना सुरक्षित ठिकाणी बांधा\n"
            msg += "• 🌊 शेताचा निचरा (drainage) तपासा\n"
        if thunderstorm:
            msg += "• 🏠 स्वतः घरात थांबा, झाडाखाली जाऊ नका\n"
        if heavy_rain:
            msg += "• 🥬 काढणीस आलेला माल सुरक्षित करा\n"
        if strong_wind:
            msg += "• 🪵 टोमॅटो व इतर पिकांना आधार द्या\n"
            msg += "• 🏠 शेडनेट व पॉलिहाउस सुरक्षित करा\n"
        if heat_wave:
            msg += "• 💧 सकाळी लवकर भरपूर पाणी द्या\n"
            msg += "• 🌿 शेडनेट वापरा, दुपारी पाणी देऊ नका\n"

        msg += f"\n*सुरक्षित रहा, पीक सांभाळा* 🌱\n"
        msg += f"📞 _किसान हेल्पलाइन: 1800-180-1551 (मोफत)_\n"
        msg += f"_— KrishiMitra 🌾_"

        return msg

    except Exception as e:
        log.error(f"_check_danger: {e}")
        return ""

async def morning():
    try:
        from app.services.database import get_all_farmers
        from app.services.weather import get_weather
        from app.services.whatsapp import send_message
        farmers = await get_all_farmers()
        log.info(f"Morning batch: {len(farmers)} farmers")
        for f in farmers:
            try:
                w = await get_weather(f.get("lat"), f.get("lon"), f.get("city", "Pune"))
                msg = f"🌅 *सुप्रभात! — KrishiMitra*\n\n{w}\n\n❓ काही प्रश्न असल्यास विचारा!"
                await send_message(f["phone"], msg)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Morning {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Morning batch: {e}")

async def evening():
    try:
        from app.services.database import get_all_farmers
        from app.services.whatsapp import send_message
        tip = _tip(datetime.now().month)
        farmers = await get_all_farmers()
        log.info(f"Evening batch: {len(farmers)} farmers")
        for f in farmers:
            try:
                await send_message(f["phone"], tip)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Evening {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Evening batch: {e}")

async def weekly():
    try:
        from app.services.database import get_all_farmers
        from app.services.mandi import get_mandi_prices
        from app.services.whatsapp import send_message
        mandi = await get_mandi_prices("Pune")
        msg = f"📊 *साप्ताहिक मंडी अहवाल — KrishiMitra*\n\n{mandi}\n\n❓ भाव किंवा शेतीबद्दल काही विचारायचे असल्यास message करा!"
        farmers = await get_all_farmers()
        log.info(f"Weekly batch: {len(farmers)} farmers")
        for f in farmers:
            try:
                await send_message(f["phone"], msg)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Weekly {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Weekly batch: {e}")

def _tip(m):
    tips = {
        1:  "❄️ *जानेवारी:* कांद्याला थंडीपासून वाचवा. खते देणे थांबवा.",
        2:  "🌸 *फेब्रुवारी:* टोमॅटोला बुरशीनाशक फवारा. कांदा काढणी तपासा.",
        3:  "☀️ *मार्च:* ऊन वाढते — पाणी जास्त द्या. कांदा साठवण सुरू करा.",
        4:  "🌡️ *एप्रिल:* टोमॅटोला शेडनेट लावा. पाणी सकाळी-सायंकाळी द्या.",
        5:  "💧 *मे:* पूर्व-मोसम तयारी. नाली साफ करा. बियाणे order करा.",
        6:  "🌧️ *जून:* पाऊस सुरू — बुरशीनाशक फवारणी तयार. निचरा तपासा.",
        7:  "🌾 *जुलै:* खरीप लावणीस वेळ. पावसात फवारणी करू नका.",
        8:  "🌿 *ऑगस्ट:* टोमॅटोला आधार द्या. कांदा रोपवाटिका तयार करा.",
        9:  "📅 *सप्टेंबर:* रब्बी तयारी. जमीन तपासणी. माती आरोग्य कार्ड काढा.",
        10: "🧅 *ऑक्टोबर:* कांदा लावणीस उत्तम वेळ. बियाणे तपासा.",
        11: "🌱 *नोव्हेंबर:* कांदा + टोमॅटोला खते द्या. हवामान थंड होते.",
        12: "❄️ *डिसेंबर:* थंडीपासून पीक वाचवा. ठिबक सिंचन तपासा.",
    }
    return (f"{tips.get(m, '🌾 KrishiMitra: पिकाची काळजी घ्या!')}\n\n"
            f"❓ प्रश्न असल्यास विचारा!\n_— KrishiMitra 🌾_")
