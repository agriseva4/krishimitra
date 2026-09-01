import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from app.services.database import (get_farmer, create_farmer, log_conv, get_last_messages,
    update_farmer_crops, update_farmer_state, update_farmer_district, update_farmer_taluka)
from app.services.ai_service import farming_answer, disease_detect, voice_to_text, CROP_KEYWORDS, DISEASE_WORDS, FERTILIZER_WORDS
from app.services.weather import get_weather
from app.services.mandi import get_mandi_prices
from app.services.whatsapp import get_media_url, download_media
from app.data.maharashtra_locations import MAHARASHTRA_DISTRICTS, DIVISIONS, get_talukas

log = logging.getLogger(__name__)

FREE_NUMBERS = []

# टीप: राज्य निवडायचा टप्पा — सध्या फक्त महाराष्ट्र आहे, पण रचना अशी आहे की भविष्यात
# अजून राज्यं (उदा. कर्नाटक, गुजरात) सहज add करता येतील — फक्त list मध्ये एक ओळ वाढवायची.
STATES = {"महाराष्ट्र": "Maharashtra"}

# जिल्ह्यांची क्रमवार यादी (विभागानुसार गटबद्ध, 1-36 सलग क्रमांक) — display आणि detection
# दोन्हीसाठी वापरली जाते, जेणेकरून numbering कधीच विसंगत होणार नाही.
def _build_district_order():
    order = []
    n = 1
    for division, keys in DIVISIONS.items():
        for k in keys:
            name = MAHARASHTRA_DISTRICTS[k][0]
            order.append((n, k, name, division))
            n += 1
    return order

DISTRICT_ORDER = _build_district_order()

def _key_from_district_name(name: str) -> str:
    """DB मध्ये district हा मराठी नावाने साठवलेला असतो — तालुका-यादी काढण्यासाठी परत key शोध"""
    for key, (dname, _, _, _) in MAHARASHTRA_DISTRICTS.items():
        if dname == name:
            return key
    return ""

def _build_state_select() -> str:
    return """🌾 *KrishiMitra मध्ये आपले स्वागत आहे!*

आधी तुमचं राज्य सांगा 👇

1️⃣ महाराष्ट्र

_सध्या फक्त महाराष्ट्रासाठी सेवा उपलब्ध आहे — लवकरच इतर राज्यंही येतील_ 📝"""

def _build_district_select() -> str:
    lines = ["✅ *राज्य: महाराष्ट्र*\n\nआता तुमचा *जिल्हा* सांगा — नंबर पाठवा 👇"]
    current_division = None
    for n, key, name, division in DISTRICT_ORDER:
        if division != current_division:
            lines.append(f"\n*{division} विभाग:*")
            current_division = division
        lines.append(f"{n}. {name}")
    lines.append("\n_जिल्ह्याचा नंबर पाठवा (उदा. 33 पुण्यासाठी)_ 📝")
    return "\n".join(lines)

def _build_taluka_select(district_key: str) -> str:
    talukas = get_talukas(district_key)
    district_name = MAHARASHTRA_DISTRICTS.get(district_key, ("",))[0]
    lines = [f"✅ *जिल्हा: {district_name}*\n\nआता तुमचा *तालुका* सांगा — नंबर पाठवा 👇\n"]
    for i, tal in enumerate(talukas, 1):
        lines.append(f"{i}. {tal}")
    lines.append("\n_तालुक्याचा नंबर पाठवा_ 📝")
    return "\n".join(lines)

def _detect_state(text: str) -> bool:
    t = text.lower().strip()
    return t in ["1", "maharashtra", "महाराष्ट्र", "mh", "maha"]

def _detect_district(text: str) -> str:
    """नंबर (1-36) किंवा जिल्ह्याचं नाव (मराठी/इंग्रजी key) — दोन्ही स्वीकारतो"""
    t = text.lower().strip()
    if t.isdigit():
        n = int(t)
        for num, key, name, division in DISTRICT_ORDER:
            if num == n:
                return key
        return ""
    for num, key, name, division in DISTRICT_ORDER:
        if key in t or name in text:
            return key
    return ""

def _detect_taluka(text: str, district_key: str) -> str:
    """नंबर किंवा तालुक्याचं नाव — त्या specific जिल्ह्याच्या यादीतून"""
    t = text.lower().strip()
    talukas = get_talukas(district_key)
    if t.isdigit():
        n = int(t)
        if 1 <= n <= len(talukas):
            return talukas[n - 1]
        return ""
    for tal in talukas:
        if tal in text:
            return tal
    return ""

WELCOME = """🙏 *नमस्कार!*
शेतीसंबंधित काहीही माहिती हवी असेल तर इथे विचारा 🌱

✅ बाजारभाव
✅ हवामान
✅ पीक सल्ला
✅ रोग उपाय
✅ व्हॉइस मेसेज 🎤

तुमचा प्रश्न पाठवा 😊
_— KrishiMitra 🌾_"""

DATE_WORDS = [
    "tarikh", "tarikh kay", "आजची तारीख", "तारीख", "date today",
    "today's date", "what date", "kay tarikh", "aajchi tarikh"
]

WEATHER_WORDS = [
    "weather", "havaman", "hawaman", "hava", "हवामान", "पाऊस", "paus", "rain",
    "ऊन", "thand", "थंडी", "temp", "temperature", "उद्या",
    "उन्हाळा", "garmi", "थंड", "warm", "cold", "forecast"
]

MANDI_WORDS = [
    "bhav", "भाव", "mandi", "मंडई", "market", "बाजार",
    "rate", "किंमत", "price", "दर",
]
# टीप: आधी "kanda", "tamatar", "aaj", "today", "आजचा" पण होते — पण हे खूप generic होते.
# "kanda" हा फक्त पिकाचं नाव आहे, price-specific नाही — त्यामुळे "kandyala rog aalay"
# (कांद्याला रोग आलाय — तातडीचा disease प्रश्न!) सुद्धा चुकून mandi price दाखवायचा,
# खरा disease सल्ला न देता. हे काढल्यामुळे आता फक्त खरे price-केंद्रित प्रश्नच match होतील.

async def handle(phone: str, message: dict, msg_type: str) -> str:
    if phone in FREE_NUMBERS:
        farmer = {"phone": phone, "is_approved": True, "is_free": True,
                  "crops": ["onion", "tomato"], "city": "Pune",
                  "district": "Pune", "lat": 18.5204, "lon": 73.8567}
        return await _route(phone, message, msg_type, farmer)

    farmer = await get_farmer(phone)

    if not farmer:
        await create_farmer(phone)
        return _build_state_select()

    if not farmer.get("is_approved"):
        return "⏳ तुमची नोंदणी मंजूर होणे बाकी आहे.\nप्रशासकाकडून लवकरच मंजुरी मिळेल. धन्यवाद! 🙏"

    if farmer.get("is_blocked"):
        return ""

    # टीप: 3-पायऱ्यांचा onboarding — राज्य → जिल्हा → तालुका. प्रत्येक पायरी क्रमाने,
    # आधीची पूर्ण झाल्याशिवाय पुढची विचारली जात नाही. location_set फक्त तिन्ही पूर्ण
    # झाल्यावरच True होतो (database.py च्या update_farmer_taluka मध्ये).
    if not farmer.get("location_set"):
        if msg_type != "text":
            # Onboarding दरम्यान photo/voice आलं तर सध्याची पायरी परत दाखव
            if not farmer.get("state"):
                return _build_state_select()
            elif not farmer.get("district"):
                return _build_district_select()
            else:
                district_key = _key_from_district_name(farmer.get("district", ""))
                return _build_taluka_select(district_key)

        text = message.get("text", {}).get("body", "").strip()

        # पायरी 1 — राज्य
        if not farmer.get("state"):
            if _detect_state(text):
                await update_farmer_state(phone, "Maharashtra")
                return _build_district_select()
            return _build_state_select()

        # पायरी 2 — जिल्हा
        if not farmer.get("district"):
            district_key = _detect_district(text)
            if district_key:
                district_name = MAHARASHTRA_DISTRICTS[district_key][0]
                await update_farmer_district(phone, district_key, district_name)
                return _build_taluka_select(district_key)
            return _build_district_select()

        # पायरी 3 — तालुका (शेवटची, यानंतर location_set = True)
        district_key = _key_from_district_name(farmer.get("district", ""))
        if not district_key:
            # असामान्य स्थिती — district नाव जुळत नाही, सुरक्षिततेसाठी परत जिल्हा विचार
            return _build_district_select()
        taluka = _detect_taluka(text, district_key)
        if taluka:
            await update_farmer_taluka(phone, taluka)
            district_name = farmer.get("district", "")
            return (f"✅ *नोंदणी पूर्ण झाली!*\n\n"
                    f"📍 जिल्हा: *{district_name}* | तालुका: *{taluka}*\n\n"
                    f"आता शेतीविषयक काहीही विचारा 🌾\n"
                    f"_— KrishiMitra_ 🙏")
        return _build_taluka_select(district_key)

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

def _scan_new_crops(text: str, existing_crops: list) -> list:
    """Message madhe konte pik mention zalay te shodh, jya already farmer.crops madhe nahit"""
    t = text.lower()
    existing_lower = [c.lower() for c in existing_crops]
    new_found = []
    for crop, keywords in CROP_KEYWORDS.items():
        if crop in existing_lower:
            continue
        if any(k in t for k in keywords):
            new_found.append(crop)
    return new_found

async def _text(phone: str, text: str, farmer: dict) -> str:
    t = text.lower().strip()

    if t in ["hi", "hello", "hey", "helo", "hii", "नमस्कार", "namaskar", "hy", "hye", "start"]:
        return WELCOME

    if any(w in t for w in DATE_WORDS):
        months_mr = ["", "जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून",
                     "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        return f"📅 आजची तारीख: *{now.day} {months_mr[now.month]} {now.year}*"

    # टीप: DISEASE_WORDS/FERTILIZER_WORDS असतील तर हवामान shortcut ने hijack करायचं नाही —
    # "थंडीमुळे पान सुकतंय" सारखा प्रश्न disease-सल्ला हवा असतो, नुसता hवामान अंदाज नाही.
    _early_disease_fert_check = any(w in t for w in DISEASE_WORDS) or any(w in t for w in FERTILIZER_WORDS)

    if any(w in t for w in WEATHER_WORDS) and not _early_disease_fert_check:
        return await get_weather(
            farmer.get("lat", 18.5204),
            farmer.get("lon", 73.8567),
            farmer.get("city", farmer.get("district", "Pune"))
        )

    # टीप: DISEASE_WORDS/FERTILIZER_WORDS असतील तर हे मंडई-भाव पेक्षा जास्त तातडीचं आहे —
    # farmer ला रोग/खताचा प्रश्न असेल तर price shortcut ने तो hijack करायचा नाही, नाहीतर
    # "कांद्याला रोग आलाय" सारखा तातडीचा प्रश्न चुकून फक्त भाव दाखवून थांबायचा.
    if any(w in t for w in MANDI_WORDS) and not _early_disease_fert_check:
        district = farmer.get("district", "Pune")
        # टीप: आधी farmer चे स्वतःचे crops कधीच पाठवले जात नव्हते — नेहमी mandi.py चा
        # default (onion/tomato) दाखवला जायचा, farmer प्रत्यक्षात काहीही पिकवत असला तरी.
        # आता farmer.crops (जर नोंदलेले असतील तर) थेट पाठवतो.
        farmer_crops = farmer.get("crops", [])
        if farmer_crops:
            return await get_mandi_prices(district, crops=farmer_crops)
        return await get_mandi_prices(district)

    # Naveen pikache naव mention zalay ka — asel tar farmer.crops madhe save kar
    existing_crops = farmer.get("crops", [])
    new_crops = _scan_new_crops(text, existing_crops)
    if new_crops:
        updated_crops = existing_crops + new_crops
        await update_farmer_crops(phone, updated_crops)
        farmer["crops"] = updated_crops  # current request sathi pan update kar

    history = await get_last_messages(phone, limit=6)
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
        history = await get_last_messages(phone, limit=6)
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
