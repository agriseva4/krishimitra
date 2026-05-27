import logging
from app.services.database import get_farmer, create_farmer, log_conv
from app.services.ai_service import farming_answer, disease_detect, scheme_info, voice_to_text
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
✅ व्हॉइस मेसेज 🎤

तुमचा प्रश्न पाठवा 😊
_— KrishiMitra 🌾_"""

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
        elif mtype in ["audio", "voice"]:
            resp = await _audio(msg, farmer)
            await log_conv(phone, "[VOICE]", resp, "audio")
            return resp
        return WELCOME
    except Exception as e:
        log.error(f"Route {phone}: {e}")
        return "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏"

async def _text(text: str, farmer: dict) -> str:
    t = text.lower().strip()

    # Hi/Hello → Welcome
    if any(w in t for w in ["hi","hello","hey","helo","hii","नमस्कार","namaskar","hy","hye"]):
        return WELCOME

    # Weather → Direct OpenWeather API (short & real)
    if any(w in t for w in ["weather","havaman","हवामान","पाऊस","paus","rain","ऊन","thand","थंडी","temp","ऊष्णता"]):
        return await get_weather(
            farmer.get("lat"),
            farmer.get("lon"),
            farmer.get("city", "Pune")
        )

    # Baaki kahihi → AI swatah detect karun answer deil
    return await farming_answer(text, farmer)

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
                    "कृपया:\n"
                    "• स्पष्टपणे बोला\n"
                    "• शांत ठिकाणी record करा\n"
                    "• किंवा टेक्स्ट मध्ये लिहा 📝")
        answer = await _text(transcribed, farmer)
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
