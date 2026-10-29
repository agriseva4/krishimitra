import logging, os
from datetime import datetime
from zoneinfo import ZoneInfo
from app.services.database import (get_farmer, create_farmer, log_conv, get_last_messages,
    update_farmer_crops, update_farmer_state, update_farmer_district, update_farmer_taluka, set_opt_out)
from app.services.ai_service import farming_answer, disease_detect, voice_to_text, CROP_KEYWORDS, DISEASE_WORDS, FERTILIZER_WORDS, any_kw, llm_understand, _detect_crops
from app.services.weather import get_weather
from app.services.mandi import get_mandi_prices
from app.services.whatsapp import get_media_url, download_media, was_nudged_recently, clear_nudge, mask_phone
from app.services.digest import build_daily_digest
from app.data.maharashtra_locations import MAHARASHTRA_DISTRICTS, DIVISIONS, get_talukas

log = logging.getLogger(__name__)

FREE_NUMBERS = []

# ── बंद / चालू (opt-out) ────────────────────────────────────────────────────
# फक्त संपूर्ण message हाच शब्द असेल तरच — "पंप बंद पडला" सारख्या प्रश्नाने चुकून बंद होऊ नये.
STOP_WORDS = {"stop", "बंद", "बंद करा", "थांबवा", "थांबा", "unsubscribe", "band", "band kara"}
START_WORDS = {"चालू", "चालू करा", "सुरू", "सुरू करा", "subscribe", "resume", "chalu", "chalu kara"}
THANKS_WORDS = {"धन्यवाद", "आभारी आहे", "आभार", "thanks", "thank you", "thankyou", "ठीक आहे", "छान", "बरं", "बर", "ok thanks"}
YES_WORDS = {"हो", "होय", "हा", "ho", "hoy", "ha", "yes", "ok", "ओके"}
PRIVACY_URL = os.getenv("PRIVACY_URL", "")

# AI ने संदेश आधी समजून घ्यायचा का?
#   "always"   = प्रत्येक प्रश्नावर AI आधी विषय (हवामान/भाव/रोग/खत) आणि पीक समजून घेतो; शब्द-यादी फक्त मदतीला.
#                मराठीतल्या कोणत्याही रूपासाठी सर्वात चांगलं. (प्रत्येक संदेशाला एक छोटा extra AI call)
#   "fallback" = शब्द जुळले नाहीत तरच AI ला विचारतो (स्वस्त/जलद, पण शब्द जुळले आणि चुकीचे असतील तर AI मदत करत नाही)
UNDERSTAND_MODE = os.getenv("UNDERSTAND_MODE", "fallback").strip().lower()   # free tier साठी "fallback" (कमी calls)

CONSENT_LINE = ("🔒 आम्ही तुमचा नंबर, पिकं आणि प्रश्न सेवा देण्यासाठी आणि सुधारण्यासाठी साठवतो. "
                "रोजचे संदेश थांबवायला कधीही *बंद* लिहा."
                + (f"\nगोपनीयता: {PRIVACY_URL}" if PRIVACY_URL else ""))

# ── दिवसाची message मर्यादा (खर्च/दुरुपयोग नियंत्रण) ────────────────────────────
DAILY_MSG_LIMIT = max(5, int(os.getenv("DAILY_MSG_LIMIT", "150")))   # सर्व संदेश (दुरुपयोग रोखायला)

# AI वापरणाऱ्या प्रश्नांची मर्यादा (free-tier quota वाचवायला): हवामान/भाव/तारीख यात मोजली जात नाहीत.
# फोटो = 2, व्हॉइस = 1, AI-उत्तर = 1.
DAILY_AI_LIMIT = max(3, int(os.getenv("DAILY_AI_LIMIT", "20")))
_ai_used = {}   # phone -> (IST तारीख, count)
AI_LIMIT_MSG = ("🙏 आजचे तुमचे प्रश्न (AI उत्तरं) संपले आहेत, उद्या पुन्हा विचारा.\n"
                "🌦️ हवामान आणि 📊 मंडई भाव कधीही विचारू शकता.\n"
                "तातडीच्या मदतीसाठी 📞 1800-180-1551 (मोफत)")

def _ai_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()

def _ai_over(phone: str) -> bool:
    d, n = _ai_used.get(phone, (_ai_today(), 0))
    return d == _ai_today() and n >= DAILY_AI_LIMIT

def _ai_use(phone: str, weight: int = 1):
    d, n = _ai_used.get(phone, (_ai_today(), 0))
    if d != _ai_today():
        n = 0
    _ai_used[phone] = (_ai_today(), n + weight)
_daily = {}   # phone -> (IST तारीख, count)

def _rate_check(phone: str) -> str:
    """"ok" | "first_block" (आजची पहिली अडवणूक — संदेश पाठव) | "blocked" (आधीच सांगितलंय — गप्प रहा)"""
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    d, n = _daily.get(phone, (today, 0))
    if d != today:
        d, n = today, 0
    n += 1
    _daily[phone] = (d, n)
    if n <= DAILY_MSG_LIMIT:
        return "ok"
    return "first_block" if n == DAILY_MSG_LIMIT + 1 else "blocked"

# ── 👍/👎 feedback — कधी विचारायचं ───────────────────────────────────────────
# AI च्या उत्तरानंतर (हवामान/भाव/तारीख नाही) बटणं पाठवतो. प्रत्येक वेळी विचारलं तर शेतकरी वैतागेल,
# म्हणून FEEDBACK_EVERY_N (default 2) = प्रत्येक दुसऱ्या AI-उत्तरानंतर; फोटो-निदानानंतर नेहमी.
FEEDBACK_EVERY_N = max(1, int(os.getenv("FEEDBACK_EVERY_N", "2")))
_fb_wanted = set()
_fb_counter = {}

def _mark_feedback(phone: str, always: bool = False):
    n = _fb_counter.get(phone, 0) + 1
    _fb_counter[phone] = n
    if always or n % FEEDBACK_EVERY_N == 0:
        _fb_wanted.add(phone)

def pop_feedback_flag(phone: str) -> bool:
    """webhook उत्तर पाठवल्यावर हे विचारतो — True असेल तर 👍/👎 बटणं पाठवा."""
    if phone in _fb_wanted:
        _fb_wanted.discard(phone)
        return True
    return False

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
    # टीप: आधी इथे "उदा. 33 पुण्यासाठी" हार्डकोड होतं — पण 33 म्हणजे भंडारा! (पुणे = 13).
    # आता उदाहरणातला नंबर यादीतूनच आपोआप काढतो, त्यामुळे यादी बदलली तरी चुकणार नाही.
    pune_n = next((n for n, k, _nm, _dv in DISTRICT_ORDER if k == "pune"), 1)
    lines.append(f"\n_जिल्ह्याचा नंबर पाठवा (उदा. {pune_n} पुण्यासाठी)_ 📝")
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
        # टीप: आधी इथे crops=["onion","tomato"] hardcoded होतं — testing/admin bypass
        # असला तरी "कधीच अंदाज नको" या तत्त्वाला अपवाद नसावा, म्हणून रिकामं ठेवलं.
        farmer = {"phone": phone, "is_approved": True, "is_free": True,
                  "crops": [], "city": "Pune",
                  "district": "Pune", "lat": 18.5204, "lon": 73.8567}
        return await _route(phone, message, msg_type, farmer)

    farmer = await get_farmer(phone)

    if not farmer:
        await create_farmer(phone)
        return ("🙏 *नमस्कार! KrishiMitra मध्ये आपले स्वागत आहे.*\n\n"
                "तुमची नोंदणी मिळाली आहे ✅\n"
                "⏳ मंजुरी मिळताच आम्ही तुम्हाला इथेच कळवू. धन्यवाद! 🌾\n\n" + CONSENT_LINE)

    if not farmer.get("is_approved"):
        return "⏳ तुमची नोंदणी मंजूर होणे बाकी आहे.\nप्रशासकाकडून लवकरच मंजुरी मिळेल. धन्यवाद! 🙏"

    if farmer.get("is_blocked"):
        return ""

    # बंद / चालू — संपूर्ण message तेवढंच असेल तर (onboarding पूर्ण नसतानाही चालतं)
    if msg_type == "text":
        _cmd = message.get("text", {}).get("body", "").strip().lower()
        if _cmd in STOP_WORDS:
            ok = await set_opt_out(phone, True)
            return ("✅ ठीक आहे, रोजचे संदेश (हवामान/भाव/सल्ला) बंद केले. 🙏\n"
                    "तुम्ही प्रश्न विचारू शकता — उत्तर मिळत राहील.\n"
                    "पुन्हा चालू करायला *चालू* लिहा." if ok else
                    "⚠️ तांत्रिक अडचण आली, कृपया थोड्या वेळाने पुन्हा *बंद* लिहा.")
        if _cmd in START_WORDS:
            ok = await set_opt_out(phone, False)
            return ("✅ रोजचे संदेश पुन्हा चालू केले. 🌾 थांबवायला *बंद* लिहा." if ok else
                    "⚠️ तांत्रिक अडचण आली, कृपया थोड्या वेळाने पुन्हा *चालू* लिहा.")

    _rl = _rate_check(phone)
    if _rl == "first_block":
        return ("🙏 आजची प्रश्नांची मर्यादा संपली आहे. उद्या पुन्हा विचारा.\n"
                "तातडीच्या मदतीसाठी 📞 1800-180-1551 (मोफत) वर संपर्क करा.")
    if _rl == "blocked":
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
        district_key = _key_from_district_name(farmer.get("district", ""))
        if not district_key:
            # district रिकामा आहे, किंवा त्यात मराठी नावाशी न जुळणारं काही आहे (उदा. SQL/admin ने
            # इंग्रजीत "Pune" भरलेलं) — दोन्ही केसमध्ये परत निवडायला लाव. (आधी इथे अनंत loop व्हायचा.)
            picked = _detect_district(text)
            if picked:
                district_name = MAHARASHTRA_DISTRICTS[picked][0]
                await update_farmer_district(phone, picked, district_name)
                return _build_taluka_select(picked)
            return _build_district_select()

        # पायरी 3 — तालुका (शेवटची, यानंतर location_set = True)
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
            if _ai_over(phone):
                resp = AI_LIMIT_MSG
            else:
                _ai_use(phone, 2)
                resp = await _image(img_id, caption, farmer)
            if resp and resp != AI_LIMIT_MSG and not resp.startswith("❌"):
                _mark_feedback(phone, always=True)
            await log_conv(phone, f"[IMAGE]{caption}", resp, "image")
            return resp
        elif mtype in ["audio", "voice"]:
            resp = await _audio(phone, msg, farmer)
            await log_conv(phone, "[VOICE]", resp, "audio")
            return resp
        return WELCOME
    except Exception as e:
        log.error(f"Route {mask_phone(phone)}: {e}")
        return "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏"

WEATHER_WORDS += ["वातावरण", "तापमान", "ढगाळ", "गारपीट", "वादळ", "वारा", "आर्द्रता", "पावस", "पावसा", "उष्ण", "उन्ह", "ऊन्ह", "vatavaran", "tapman", "pavsa", "pavus"]
MANDI_WORDS += ["रेट", "मंडी", "आवक", "बाजारात", "विकलं", "विकतोय", "bajar", "bajarbhav", "mandit"]

def _scan_new_crops(text: str, existing_crops: list) -> list:
    """Message madhe konte pik mention zalay te shodh, jya already farmer.crops madhe nahit"""
    t = text.lower()
    existing_lower = [c.lower() for c in existing_crops]
    new_found = []
    for crop, keywords in CROP_KEYWORDS.items():
        if crop in existing_lower:
            continue
        if any_kw(keywords, t, crop_mode=True):
            new_found.append(crop)
    return new_found

async def _text(phone: str, text: str, farmer: dict) -> str:
    t = text.lower().strip()

    # nudge template ला शेतकऱ्याने "हो" म्हटलं — आता 24-तास window उघडलीय, आजचं हवामान+भाव पाठव.
    # (फक्त nudge नंतरच; onboarding पूर्ण नसेल तर "हो" सामान्य flow कडेच जातं.)
    if t in YES_WORDS and farmer.get("location_set") and was_nudged_recently(phone):
        clear_nudge(phone)
        return await build_daily_digest(farmer)

    if t in ["hi", "hello", "hey", "helo", "hii", "नमस्कार", "namaskar", "hy", "hye", "start"]:
        return WELCOME

    if any_kw(DATE_WORDS, t):
        months_mr = ["", "जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून",
                     "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
        now = datetime.now(ZoneInfo("Asia/Kolkata"))
        return f"📅 आजची तारीख: *{now.day} {months_mr[now.month]} {now.year}*"

    # टीप: DISEASE_WORDS/FERTILIZER_WORDS असतील तर हवामान shortcut ने hijack करायचं नाही —
    # "थंडीमुळे पान सुकतंय" सारखा प्रश्न disease-सल्ला हवा असतो, नुसता hवामान अंदाज नाही.
    _early_disease_fert_check = any_kw(DISEASE_WORDS, t) or any_kw(FERTILIZER_WORDS, t)

    if t in THANKS_WORDS:
        return "🙏 धन्यवाद! आणखी काही विचारायचं असेल तर कधीही विचारा 🌾"

    # टीप: हवामान/भाव/रोग/खत/पीक — यापैकी कुठलाच शब्द जुळला नाही तर (मराठी रूपं, चुकीचे spelling) शेवटचा
    # आधार म्हणून LLM ला विचार: हा संदेश कशाबद्दल आहे आणि कोणतं पीक. (शब्द जुळले असतील तर LLM call होत नाही.)
    _is_weather = any_kw(WEATHER_WORDS, t)
    _is_mandi = any_kw(MANDI_WORDS, t)
    _q_crops = _detect_crops(t, [])
    _symptom = _early_disease_fert_check        # रोग/कीड/खत प्रश्न — हवामान/भाव shortcut ने hijack करू नये
    hint = None
    _kw_hit = _is_weather or _is_mandi or _early_disease_fert_check or bool(_q_crops)
    if len(t) >= 5 and (UNDERSTAND_MODE == "always" or not _kw_hit) and not _ai_over(phone):
        hint = await llm_understand(text)
        _intent = (hint or {}).get("intent")
        if _intent == "thanks":
            return "🙏 धन्यवाद! आणखी काही विचारायचं असेल तर कधीही विचारा 🌾"
        # शब्द-यादी आणि AI दोघांचे निष्कर्ष एकत्र (union) — एकाने चूक केली तर दुसरा सांभाळतो
        _is_weather = _is_weather or (_intent == "weather")
        _is_mandi = _is_mandi or (_intent == "mandi")
        _symptom = _symptom or (_intent in ("disease", "fertilizer"))
        _q_crops = list(dict.fromkeys(list(_q_crops) + list((hint or {}).get("crops", []) or [])))

    if _is_weather and not _symptom:
        return await get_weather(
            farmer.get("lat", 18.5204),
            farmer.get("lon", 73.8567),
            farmer.get("city", farmer.get("district", "Pune"))
        )

    # टीप: DISEASE_WORDS/FERTILIZER_WORDS असतील तर हे मंडई-भाव पेक्षा जास्त तातडीचं आहे —
    # farmer ला रोग/खताचा प्रश्न असेल तर price shortcut ने तो hijack करायचा नाही, नाहीतर
    # "कांद्याला रोग आलाय" सारखा तातडीचा प्रश्न चुकून फक्त भाव दाखवून थांबायचा.
    if _is_mandi and not _symptom:
        district = farmer.get("district", "Pune")
        # टीप: आधी farmer चे स्वतःचे crops कधीच पाठवले जात नव्हते — नेहमी mandi.py चा
        # default (onion/tomato) दाखवला जायचा, farmer प्रत्यक्षात काहीही पिकवत असला तरी.
        # आता farmer.crops (जर नोंदलेले असतील तर) थेट पाठवतो.
        # टीप: शेतकऱ्याने प्रश्नात ज्या पिकाचा भाव विचारला तेच आधी ("टोमॅटोचा भाव" → टोमॅटो), नाहीतर नोंदलेली पिकं.
        # (आधी नेहमी नोंदलेल्या पिकांचेच भाव यायचे, प्रश्नात काहीही असलं तरी.)
        farmer_crops = _q_crops or farmer.get("crops", [])
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

    if _ai_over(phone):
        return AI_LIMIT_MSG
    _ai_use(phone)
    history = await get_last_messages(phone, limit=6)
    ans = await farming_answer(text, farmer, history, hint=hint)
    if ans and not ans.startswith("❌"):
        _mark_feedback(phone)
    return ans

async def _audio(phone: str, msg: dict, farmer: dict) -> str:
    if _ai_over(phone):
        return AI_LIMIT_MSG
    _ai_use(phone)
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
                    "• शांत ठिकाणी बोलून पाठवा\n"
                    "• किंवा टेक्स्ट मध्ये लिहा 📝")
        history = await get_last_messages(phone, limit=6)
        answer = await farming_answer(transcribed, farmer, history)
        if answer and not answer.startswith("❌"):
            _mark_feedback(phone)
        return f"🎤 *तुम्ही म्हणालात:* _{transcribed}_\n\n{answer}"
    except Exception as e:
        log.error(f"Audio error: {e}")
        return "❌ *व्हॉइस समजला नाही.*\nटेक्स्ट मध्ये विचारा. 🙏"

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
