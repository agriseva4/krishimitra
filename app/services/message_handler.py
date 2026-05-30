import logging
from app.services.database import get_farmer, create_farmer, log_conv, get_last_messages, update_farmer_location
from app.services.ai_service import farming_answer, disease_detect, voice_to_text
from app.services.weather import get_weather
from app.services.mandi import get_mandi_prices
from app.services.whatsapp import get_media_url, download_media

log = logging.getLogger(__name__)

FREE_NUMBERS = []

# ── District → Markets Mapping ─────────────────────────────────────────────
DISTRICT_MARKETS = {
    "pune":       {"lat": 18.5204, "lon": 73.8567, "markets": ["Pune", "Pimpri"]},
    "nashik":     {"lat": 20.0059, "lon": 73.7897, "markets": ["Lasalgaon", "Pimpalgaon", "Ozar", "Rahuri"]},
    "solapur":    {"lat": 17.6599, "lon": 75.9064, "markets": ["Solapur", "Pandharpur"]},
    "ahmednagar": {"lat": 19.0948, "lon": 74.7480, "markets": ["Rahuri", "Shrirampur", "Ahmednagar"]},
    "mumbai":     {"lat": 19.0760, "lon": 72.8777, "markets": ["Vashi"]},
    "sangli":     {"lat": 16.8524, "lon": 74.5815, "markets": ["Sangli", "Miraj"]},
    "satara":     {"lat": 17.6805, "lon": 74.0183, "markets": ["Satara", "Karad"]},
    "kolhapur":   {"lat": 16.7050, "lon": 74.2433, "markets": ["Kolhapur"]},
    "jalgaon":    {"lat": 21.0077, "lon": 75.5626, "markets": ["Jalgaon", "Bhusawal"]},
    "aurangabad": {"lat": 19.8762, "lon": 75.3433, "markets": ["Aurangabad", "Lasur"]},
    "latur":      {"lat": 18.4088, "lon": 76.5604, "markets": ["Latur", "Udgir"]},
    "osmanabad":  {"lat": 18.1860, "lon": 76.0391, "markets": ["Osmanabad"]},
    "nanded":     {"lat": 19.1383, "lon": 77.3210, "markets": ["Nanded", "Mudkhed"]},
    "dhule":      {"lat": 20.9042, "lon": 74.7749, "markets": ["Dhule", "Shirpur"]},
}

# ── District Selection Message ─────────────────────────────────────────────
DISTRICT_SELECT = """🌾 *KrishiMitra मध्ये आपले स्वागत आहे!*

तुमचा जिल्हा सांगा — त्यानुसार हवामान व मंडई भाव मिळेल 👇

1️⃣ पुणे
2️⃣ नाशिक
3️⃣ सोलापूर
4️⃣ अहमदनगर
5️⃣ मुंबई / वाशी
6️⃣ सांगली
7️⃣ सातारा
8️⃣ कोल्हापूर
9️⃣ जळगाव
🔟 औरंगाबाद
1️⃣1️⃣ लातूर
1️⃣2️⃣ नांदेड

_किंवा तुमच्या जिल्ह्याचे नाव थेट लिहा_ 📝"""

WELCOME = """🙏 *नमस्कार!*
शेतीसंबंधित काहीही माहिती हवी असेल तर इथे विचारा 🌱

✅ बाजारभाव
✅ हवामान
✅ पीक सल्ला
✅ रोग उपाय
✅ व्हॉइस मेसेज 🎤

तुमचा प्रश्न पाठवा 😊
_— KrishiMitra 🌾_"""

# ── District Detection ─────────────────────────────────────────────────────
DISTRICT_KEYWORDS = {
    "pune": ["pune", "पुणे", "1"],
    "nashik": ["nashik", "nasik", "नाशिक", "2"],
    "solapur": ["solapur", "सोलापूर", "3"],
    "ahmednagar": ["ahmednagar", "nagar", "अहमदनगर", "4"],
    "mumbai": ["mumbai", "vashi", "मुंबई", "वाशी", "5"],
    "sangli": ["sangli", "सांगली", "6"],
    "satara": ["satara", "सातारा", "7"],
    "kolhapur": ["kolhapur", "कोल्हापूर", "8"],
    "jalgaon": ["jalgaon", "जळगाव", "9"],
    "aurangabad": ["aurangabad", "औरंगाबाद", "10"],
    "latur": ["latur", "लातूर", "11"],
    "nanded": ["nanded", "नांदेड", "12"],
}

def _detect_district(text: str) -> str:
    t = text.lower().strip()
    for district, keywords in DISTRICT_KEYWORDS.items():
        if any(k in t for k in keywords):
            return district
    return ""

async def handle(phone: str, message: dict, msg_type: str) -> str:
    if phone in FREE_NUMBERS:
        farmer = {"phone": phone, "is_approved": True, "is_free": True,
                  "crops": ["onion", "tomato"], "city": "Pune",
                  "district": "Pune", "lat": 18.5204, "lon": 73.8567}
        return await _route(phone, message, msg_type, farmer)

    farmer = await get_farmer(phone)

    if not farmer:
        await create_farmer(phone)
        return DISTRICT_SELECT

    if not farmer.get("is_approved"):
        return "⏳ तुमची नोंदणी approve होणे बाकी आहे.\nAdmin लवकरच करील. धन्यवाद! 🙏"

    if farmer.get("is_blocked"):
        return ""

    # District set nahi asel tar vichar
    if not farmer.get("district") or farmer.get("district") == "Pune" and not farmer.get("location_set"):
        if msg_type == "text":
            text = message.get("text", {}).get("body", "").strip()
            district = _detect_district(text)
            if district:
                info = DISTRICT_MARKETS[district]
                await update_farmer_location(phone, district, info)
                markets = ", ".join(info["markets"])
                return (f"✅ *{district.capitalize()} जिल्हा set झाला!*\n\n"
                        f"📍 तुमच्या जवळच्या मंडया: *{markets}*\n\n"
                        f"आता शेतीविषयक काहीही विचारा 🌾\n"
                        f"_— KrishiMitra_ 🙏")

    return await _route(phone, message, msg_type, farmer)

async def _route(phone, msg, mtype, farmer):
    try:
        if mtype == "text":
            text = msg.get("text", {}).get("body", "").strip()
            if not text: return WELCOME
            resp = await _text(phone, text, farmer)
            await log_conv(phone, text, resp, "text")
            return resp
        elif mtype == "image":
            img_id = msg.get("image", {}).get("id", "")
            caption = msg.get("image", {}).get("caption", "")
            resp = await _image(img_id, caption, farmer)
            await log_conv(phone, f"[IMAGE]{caption}", resp, "image")
            return resp
        elif mtype in ["audio", "voice"]:
            resp = await _audio(msg, farmer)
            await log_conv(phone, "[VOICE]", resp, "audio")
            return resp
        return WELCOME
    except Exception as e:
        log.error(f"Route {phone}: {e}")
        return "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏"

async def _text(phone: str, text: str, farmer: dict) -> str:
    t = text.lower().strip()

    # Hi/Hello → Welcome
    if t in ["hi","hello","hey","helo","hii","नमस्कार","namaskar","hy","hye","start"]:
        return WELCOME

    # Weather → Direct OpenWeather API — farmer chya location nusar
    if any(w in t for w in ["weather","havaman","हवामान","पाऊस","paus","rain","ऊन","thand","थंडी","temp"]):
        return await get_weather(
            farmer.get("lat", 18.5204),
            farmer.get("lon", 73.8567),
            farmer.get("city", farmer.get("district", "Pune"))
        )

    # Mandi → farmer chya district nusar
    if any(w in t for w in ["bhav","भाव","mandi","मंडई","market","बाजार","rate","किंमत"]):
        district = farmer.get("district", "Pune")
        return await get_mandi_prices(district)

    # Conversation history fetch
    history = await get_last_messages(phone, limit=3)

    # AI la pathav
    return await farming_answer(text, farmer, history)

async def _audio(msg: dict, farmer: dict) -> str:
    try:
        audio_data = msg.get("audio") or msg.get("voice") or {}
        audio_id = audio_data.get("id", "")
        if not audio_id:
            return "❌ *व्हॉइस मेसेज मिळाला नाही.*\nपुन्हा पाठवा. 🎤"
        url = await get_media_url(audio_id)
        if not url:
            return "❌ *व्हॉइस डाउनलोड करता आला नाही.*\nपुन्हा पाठवा. 🎤"
        audio_bytes = await download_media(url)
        if not audio_bytes:
            return "❌ *व्हॉइस रिकामा आहे.*\nस्पष्टपणे बोलून पाठवा. 🎤"
        transcribed = await voice_to_text(audio_bytes)
        if not transcribed:
            return ("🎤 *व्हॉइस ऐकला, पण नीट समजला नाही.*\n\n"
                    "कृपया:\n• स्पष्टपणे बोला\n"
                    "• शांत ठिकाणी record करा\n"
                    "• किंवा टेक्स्ट मध्ये लिहा 📝")
        history = await get_last_messages(phone, limit=3)
        answer = await farming_answer(transcribed, farmer, history)
        return f"🎤 *तुम्ही म्हणालात:* _{transcribed}_\n\n{answer}"
    except Exception as e:
        log.error(f"Audio error: {e}")
        return "❌ *व्हॉइस process करता आला नाही.*\nटेक्स्ट मध्ये विचारा. 🙏"

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
