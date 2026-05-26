import logging
from app.services.database import get_farmer, create_farmer, log_conv
from app.services.ai_service import farming_answer, disease_detect, scheme_info
from app.services.mandi import get_mandi_prices, get_trend, CROP_MAP
from app.services.weather import get_weather
from app.services.whatsapp import get_media_url, download_media

log = logging.getLogger(__name__)

FREE_NUMBERS = []

WELCOME = """🙏 *नमस्कार!*
शेतीसंबंधित काहीही माहिती हवी असेल तर इथे विचारा 🌱

✅ बाजारभाव
✅ हवामान
✅ पीक सल्ला
✅ रोग उपाय

तुमचा प्रश्न पाठवा 😊
_— KrishiMitra 🌾_"""

HELP = """🌾 *KrishiMitra — तुमचा AI शेतकरी मित्र*

*काय विचारता येते:*

1️⃣ *पीक रोग* 🔬 — पिकाचा फोटो पाठवा
2️⃣ *खते / फवारणी* 🧪 — \"कांद्यासाठी खत सांग\"
3️⃣ *मंडी भाव* 📊 — \"आजचे मंडी भाव\"
4️⃣ *हवामान* 🌦️ — \"आजचे हवामान सांग\"
5️⃣ *सरकारी योजना* 🏛️ — \"PM किसान सांग\"
6️⃣ *कोणताही प्रश्न* 💬 — मराठीत विचारा

━━━━━━━━━━━━
📞 *किसान हेल्पलाइन:* 1800-180-1551 (मोफत)
_KrishiMitra — शेतकऱ्यांसाठी_ 🙏"""

async def handle(phone: str, message: dict, msg_type: str) -> str:
    if phone in FREE_NUMBERS:
        farmer = {"phone": phone, "is_approved": True, "is_free": True,
                  "crops": ["onion", "tomato"], "city": "Pune",
                  "district": "Pune", "lat": 18.5204, "lon": 73.8567}
        return await _route(phone, message, msg_type, farmer)

    farmer = await get_farmer(phone)

    if not farmer:
        await create_farmer(phone)
        return ("🌾 *KrishiMitra मध्ये स्वागत!*\n\n"
                "तुमची नोंदणी मिळाली! ✅\n"
                "Admin २४ तासात approve करील.\n\n"
                "Approve झाल्यावर message येईल. 🙏\n\n"
                "_KrishiMitra — तुमचा विश्वासनीय शेतकरी मित्र_")

    if not farmer.get("is_approved"):
        return "⏳ तुमची नोंदणी approve होणे बाकी आहे.\nAdmin लवकरच करील. धन्यवाद! 🙏"

    if farmer.get("is_blocked"):
        return ""

    return await _route(phone, message, msg_type, farmer)

async def _route(phone, msg, mtype, farmer):
    try:
        if mtype == "text":
            text = msg.get("text", {}).get("body", "").strip()
            if not text: return WELCOME
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
            return "🎤 व्हॉइस सपोर्ट लवकरच येणार!\nसध्या टेक्स्ट मध्ये पाठवा. 🙏"
        return WELCOME
    except Exception as e:
        log.error(f"Route {phone}: {e}")
        return "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏"

async def _text(text: str, farmer: dict) -> str:
    t = text.lower().strip()
    district = farmer.get("district", "Pune")

    # Hi/Hello → Welcome
    if any(w in t for w in ["hi","hello","hey","helo","hii","नमस्कार","namaskar","hy","hye"]):
        return WELCOME

    # Short replies → AI la pathav
    if t in ["okay","ok","हो","yes","हां","thanks","thank you","👍","theek","theek ahe","accha","ठीक","बरं","बरे"]:
        return await farming_answer(text, farmer)

    # Help menu
    if any(w in t for w in ["help","madad","मदत","मदद","start","menu"]):
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

    # AI Q&A
    return await farming_answer(text, farmer)

async def _image(img_id, caption, farmer):
    if not img_id: return "❌ *फोटो मिळाला नाही.*\nकृपया पुन्हा पाठवा. 📸"
    try:
        url = await get_media_url(img_id)
        if not url: return "❌ *फोटो डाउनलोड करता आला नाही.*\nकृपया पुन्हा पाठवा. 📸"
        data = await download_media(url)
        if not data: return "❌ *फोटो रिकामा आहे.*\nस्वच्छ फोटो पाठवा. 📸"
        return await disease_detect(data, caption, farmer)
    except Exception as e:
        log.error(f"Image {e}")
        return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"
