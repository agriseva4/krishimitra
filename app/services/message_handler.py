import logging
from app.services.database import get_farmer, create_farmer, log_conv
from app.services.ai_service import farming_answer, disease_detect, scheme_info
from app.services.mandi import get_mandi_prices, get_trend, CROP_MAP
from app.services.weather import get_weather
from app.services.whatsapp import get_media_url, download_media

log = logging.getLogger(__name__)

FREE_NUMBERS = [
    # "919XXXXXXXXX",  # Tumcha number uncomment kara
]

HELP = """🌾 *KrishiMitra — Tumcha AI Shetkari Mitra*
_Pune | Marathi | Hindi | English_

*Kay vicharata yete:*

1️⃣ *Pik Rog* 🔬
   Pikachi photo pathva — AI diagnosis milel

2️⃣ *Khate / Fawara* 🧪
   "कांद्यासाठी खत सांग"
   "टोमॅटोला किती पाणी द्यावे"

3️⃣ *Live Mandi Bhav* 📊
   "आजचे मंडी भाव"
   "कांदा भाव" / "टोमॅटो भाव"

4️⃣ *Price Trend* 📈
   "कांदा trend" / "टोमॅटो trend"

5️⃣ *Havaman* 🌦️
   "आजचे हवामान सांग"

6️⃣ *Sarkar Yojana* 🏛️
   "PM किसान सांग" / "पीक विमा माहिती"

7️⃣ *Koni pn Prashn* 💬
   Marathi / Hindi / English madhe

━━━━━━━━━━━━
📞 *Kisan Helpline:* 1800-180-1551 (Free)
_KrishiMitra — Shetkaryasathi, Shetkaryani_ 🙏"""

async def handle(phone: str, message: dict, msg_type: str) -> str:
    # Free numbers — always approved
    if phone in FREE_NUMBERS:
        farmer = {"phone": phone, "is_approved": True, "is_free": True,
                  "crops": ["onion", "tomato"], "city": "Pune",
                  "district": "Pune", "lat": 18.5204, "lon": 73.8567}
        return await _route(phone, message, msg_type, farmer)

    farmer = await get_farmer(phone)

    if not farmer:
        await create_farmer(phone)
        return ("🌾 *KrishiMitra madhe Swagat!*\n\n"
                "Tumchi nondani milali! ✅\n"
                "Admin 24 tasaat approve karil.\n\n"
                "Approve zhalyavar message yeil. 🙏\n\n"
                "_KrishiMitra — Tumcha Vishwasniya Shetkari Mitra_")

    if not farmer.get("is_approved"):
        return "⏳ Tumchi nondani approve hone baaki ahe.\nAdmin lवkarach karil. Dhanyavad! 🙏"

    if farmer.get("is_blocked"):
        return ""

    return await _route(phone, message, msg_type, farmer)

async def _route(phone, msg, mtype, farmer):
    try:
        if mtype == "text":
            text = msg.get("text", {}).get("body", "").strip()
            if not text: return HELP
            resp = await _text(text, farmer)
            await log_conv(phone, text, resp, "text")
            return resp
        elif mtype == "image":
            img_id = msg.get("image", {}).get("id", "")
            caption = msg.get("image", {}).get("caption", "")
            resp = await _image(img_id, caption, farmer)
            await log_conv(phone, f"[IMAGE]{caption}", resp, "image")
            return resp
        elif mtype == "audio":
            return "🎤 Voice support lavkarach!\nAthasathi text madhe pathva. 🙏"
        return HELP
    except Exception as e:
        log.error(f"Route {phone}: {e}")
        return "❌ Thodi adchan aali. Parat prayatna kara. 🙏"

async def _text(text: str, farmer: dict) -> str:
    t = text.lower().strip()
    district = farmer.get("district", "Pune")

    # Help
    if any(w in t for w in ["help","madad","मदत","मदद","start","menu","hi","hello","नमस्कार","namaskar","hey"]):
        return HELP

    # Trend
    if "trend" in t:
        crop = "Onion"
        for k, v in CROP_MAP.items():
            if k in t:
                crop = v
                break
        return await get_trend(crop, district)

    # Specific crop price
    price_words = ["bhav", "भाव", "rate", "price", "किंमत", "dar"]
    for k, v in CROP_MAP.items():
        if k in t and any(w in t for w in price_words):
            return await get_mandi_prices(district, k)

    # All mandi
    if any(w in t for w in ["mandi","मंडी","bhav","भाव","market","बाजार","bajar","rate"]):
        return await get_mandi_prices(district)

    # Weather
    if any(w in t for w in ["weather","havaman","हवामान","पाऊस","paus","rain","una","thand","temp"]):
        return await get_weather(farmer.get("lat"), farmer.get("lon"), farmer.get("city"))

    # Schemes
    if any(w in t for w in ["yojana","योजना","scheme","sarkar","vima","विमा","kisan","किसान","subsidy","loan","कर्ज","insurance"]):
        return await scheme_info(text)

    # AI Q&A — everything else
    return await farming_answer(text, farmer)

async def _image(img_id, caption, farmer):
    if not img_id: return "❌ Photo milali nahi. Parat pathva."
    try:
        url = await get_media_url(img_id)
        if not url: return "❌ Photo download karta ali nahi. Parat pathva."
        data = await download_media(url)
        if not data: return "❌ Photo empty ahe. Saaf photo pathva."
        return await disease_detect(data, caption, farmer)
    except Exception as e:
        log.error(f"Image {e}")
        return "❌ Photo process karta ali nahi.\nSaaf, prakashit photo pathva. 🙏"
