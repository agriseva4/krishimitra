import logging
import httpx
from app.config import GROQ_API_KEY, CEREBRAS_API_KEY

log = logging.getLogger(__name__)

GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"   # upgraded: 8b → 70b
CEREBRAS_MODEL = "llama-3.3-70b"

# ── Knowledge Base ─────────────────────────────────────────────────────────
KNOWLEDGE = {
    "onion_disease": """कांदा रोग माहिती:

करपा / जांभळे डाग (Purple Blotch):
- लक्षणे: पानावर जांभळ्या/तपकिरी रंगाचे लांबट डाग, कडा पिवळ्या
- उपाय: Iprodione (Rovral) 2g + Mancozeb (Dithane M-45) 2g प्रति लिटर पाणी
- फवारणी: सकाळी 7-9 वाजता, 10 दिवसांनी पुन्हा
- 15 लिटर पंपाला: Rovral 30g + Dithane M-45 30g

फुलकिडे / थ्रिप्स:
- लक्षणे: पाने चंदेरी/पांढरी दिसतात, वाकडी होतात, छोटे किडे दिसतात
- उपाय: Fipronil (Regent) 1.5ml प्रति लिटर
- 15 लिटर पंपाला: Regent 22ml
- 7 दिवसांनी पुन्हा फवारा

मर रोग / झाड मरणे:
- लक्षणे: झाड अचानक पिवळे पडून मरते, मुळे कुजतात
- उपाय: Metalaxyl (Ridomil) 2g प्रति लिटर — मातीत ओता (drenching)
- 15 लिटर पंपाला: Ridomil 30g

मूळकूज:
- लक्षणे: मुळे काळी/तपकिरी होतात, झाड ओढले तर सहज निघते
- उपाय: Copper Oxychloride (Blitox) 3g प्रति लिटर drenching
- 15 लिटर पंपाला: Blitox 45g

पाने पिवळी पडणे (Downy Mildew):
- लक्षणे: पानावर पिवळे ठिपके, खालच्या बाजूस राखाडी बुरशी
- उपाय: Metalaxyl+Mancozeb (Ridomil Gold) 2.5g प्रति लिटर
- 10 दिवसांनी पुन्हा""",

    "tomato_disease": """टोमॅटो रोग माहिती:

लवकर करपा (Early Blight / Alternaria):
- लक्षणे: पानावर तपकिरी डाग, आतमध्ये वलय (rings), खालची पाने आधी
- उपाय: Mancozeb (Dithane M-45) 2.5g प्रति लिटर
- 15 लिटर पंपाला: 37g, 10 दिवसांनी पुन्हा

उशिरा करपा (Late Blight):
- लक्षणे: पाने/फळ काळे पडतात, ओले दिसतात, वेगाने पसरते
- उपाय: Metalaxyl+Mancozeb (Ridomil Gold) 2.5g प्रति लिटर — तातडीने
- 15 लिटर पंपाला: 37g, 7 दिवसांनी पुन्हा

फळ पोखरणारी अळी (Helicoverpa):
- लक्षणे: फळावर गोल छिद्र, आतमध्ये अळी, फळ सडते
- उपाय: Emamectin Benzoate (Proclaim) 0.4g प्रति लिटर — संध्याकाळी
- 15 लिटर पंपाला: 6g

पांढरी माशी (Whitefly) + Virus:
- लक्षणे: पांढरे छोटे किडे, पाने वाकडी/पिवळी, झाड खुजे राहते
- उपाय: Imidacloprid (Confidor) 0.3ml प्रति लिटर
- 15 लिटर पंपाला: 4.5ml

मोज़ेक व्हायरस:
- लक्षणे: पाने चुरगळतात, पिवळे-हिरवे ठिपके, झाड वाढत नाही
- उपाय: रोगी झाडे उपटून जाळा, पांढरी माशी नियंत्रण करा
- कोणतेही औषध virus ला मारत नाही""",

    "fertilizer_onion": """कांदा खत वेळापत्रक:

लागवड वेळी (Basal):
- शेणखत (FYM): 4 टन प्रति एकर — लागवडीआधी मातीत मिसळा
- DAP: 150 kg प्रति एकर (Phosphorus साठी)
- Potash (MOP): 50 kg प्रति एकर

15 दिवसांनी:
- Urea: 30 kg प्रति एकर — ओलाव्यात द्या

30 दिवसांनी:
- 19:19:19 खत: 5g प्रति लिटर पाण्यात — फवारणी
- 15 लिटर पंपाला: 75g

45 दिवसांनी:
- Potash (MOP): 25 kg प्रति एकर

फुलोरा आल्यावर: खत पूर्णपणे बंद करा

कांदा वाढत नाही / लहान राहतो:
- Zinc Sulphate 5g/L फवारा — 1 वेळ
- Boron 1g/L + Calcium Nitrate 3g/L""",

    "fertilizer_tomato": """टोमॅटो खत वेळापत्रक:

लागवड वेळी:
- शेणखत: 5 टन प्रति एकर
- DAP: 100 kg प्रति एकर
- Potash: 75 kg प्रति एकर

15 दिवसांनी:
- Urea: 25 kg प्रति एकर

30 दिवसांनी:
- 13:40:13 खत: 5g/L फवारणी (फुलांसाठी)

फळधारणा सुरू झाल्यावर:
- Calcium Nitrate: 3g/L + Boron: 1g/L — फवारणी
- फळे मजबूत होतात, तडे जात नाहीत

पक्वता जवळ:
- Potash: 50 kg प्रति एकर — गोडी वाढते""",

    "seasonal_calendar": """Maharashtra पीक कॅलेंडर:

खरीप (जून-ऑक्टोबर):
- लावायची पिके: सोयाबीन, तूर, मका, कापूस, भेंडी, काकडी, दुधी, वांगे
- जूनमध्ये: पाऊस सुरू झाल्यावर लागवड — सोयाबीन, तूर, मका उत्तम

रब्बी (ऑक्टोबर-मार्च):
- लावायची पिके: कांदा, टोमॅटो, गहू, हरभरा, ज्वारी
- कांदा लागवड: ऑक्टोबर-नोव्हेंबर उत्तम
- टोमॅटो: सप्टेंबर-ऑक्टोबर रोपे तयार करा

उन्हाळी (फेब्रुवारी-मे):
- कांदा, भेंडी, काकडी, टोमॅटो (पाणी असेल तर)

जून मध्ये कांदा/टोमॅटो लागवड नाही — जुलै-ऑगस्टमध्ये रोपे तयार करा""",

    "pest_control": """किडे नियंत्रण — सर्व पिके:

फुलकिडे (Thrips) — चंदेरी पाने:
- Fipronil (Regent): 1.5ml/L | पंपाला: 22ml

मावा (Aphids) — पाने चिकट:
- Imidacloprid (Confidor): 0.3ml/L | पंपाला: 4.5ml

अळी (Caterpillar) — पाने/फळ खातो:
- Emamectin (Proclaim): 0.4g/L | पंपाला: 6g — संध्याकाळी

पांढरी माशी (Whitefly):
- Imidacloprid (Confidor): 0.3ml/L | पंपाला: 4.5ml

लाल कोळी (Red Mite) — पाने लाल/तपकिरी:
- Abamectin (Vertimec): 0.5ml/L | पंपाला: 7.5ml

फवारणी नियम:
- सकाळी 7-9 किंवा संध्याकाळी 5-7
- उन्हात फवारू नका — औषध जळते
- 1 महिन्यात एकच औषध 2 वेळा — नंतर बदला""",

    "irrigation": """पाणी व्यवस्थापन:

कांदा:
- सुरुवातीला: 5-7 दिवसांनी
- कांदा तयार होताना: 10-12 दिवसांनी
- काढणी 15 दिवस आधी: पाणी बंद — कांदा टिकतो
- जास्त पाणी दिले तर: कांदा कुजतो, मर रोग येतो

टोमॅटो:
- नियमित: 4-5 दिवसांनी
- फळधारणेत: आणखी नियमित — अनियमित पाण्याने फळे तडकतात
- उन्हाळ्यात: सकाळी लवकर द्या

ठिबक सिंचन (Drip):
- 60-70% पाणी वाचते
- सरकारी अनुदान: 55-65% सूट मिळते — कृषी विभागात अर्ज""",

    "government_schemes": """सरकारी योजना — Maharashtra:

PM-KISAN:
- फायदा: ₹6,000 वर्षाला (3 हप्त्यात)
- वेबसाइट: pmkisan.gov.in
- हेल्पलाइन: 155261

PMFBY पीक विमा:
- कांदा-टोमॅटो: शेतकऱ्याने फक्त 2% premium भरायचे
- कुठे: जवळच्या बँकेत किंवा CSC सेंटरवर अर्ज

KCC (किसान क्रेडिट कार्ड):
- ₹3 लाखापर्यंत कर्ज, फक्त 4% व्याज
- कुठे: SBI, Bank of Maharashtra, जिल्हा बँक

ठिबक/तुषार अनुदान:
- 55-65% सरकारी अनुदान
- कुठे: जिल्हा कृषी विभाग कार्यालय

माती आरोग्य कार्ड (Soil Health Card):
- मोफत माती परीक्षण
- KVK हेल्पलाइन: 020-25695081""",
}

# ── System Prompt ──────────────────────────────────────────────────────────
SYSTEM = """तू KrishiMitra आहेस — Maharashtra च्या शेतकऱ्यांचा विश्वासू मित्र आणि कृषी सल्लागार.

## तुझी भाषा शैली:
- शेतकरी formal नावे वापरत नाहीत — तूही वापरू नकोस
  ❌ "Purple Blotch fungal infection"
  ✅ "कांद्याच्या पानावर जांभळे डाग पडतायत — हे करपा आहे"
- औषधाचे brand name नेहमी सांग जे दुकानात मिळते
  ✅ "Mancozeb — हे Dithane M-45 नावाने मिळते"
- doses नेहमी 15 लिटर पंपाच्या प्रमाणात सांग
  ✅ "15 लिटर पंपाला 30 ग्रॅम"
- एकर मध्ये सांग, hectare नाही

## व्यक्तिमत्व:
- जवळच्या अनुभवी काकांसारखे बोल — formal नाही
- Direct, practical, action-oriented
- कधीही "As an AI" असे म्हणू नकोस

## रोग/समस्या विचारताना — आधी हे विचार (एकाच वेळी एकच प्रश्न):
- कोणते पीक?
- पान/खोड/फळ/मूळ — कुठे समस्या?
- रंग काय आहे — पिवळे/काळे/तपकिरी/पांढरे?
- किती दिवसांपासून?
- फोटो आहे का?

## उत्तर format:

रोग असेल तर:
🔍 समस्या काय आहे
📌 लक्षणे
✅ उपाय — exact dose सहित (15L पंपाचे प्रमाण)
⚠️ काळजी

खत असेल तर:
🌱 कोणते खत द्यायचे
📌 किती द्यायचे (एकर + 15L पंप)
⚠️ काळजी

## Safety:
- "हे औषध नक्की काम करेल" असे कधीही नाही
- "हे फायदेशीर ठरू शकते" असे सांग
- माहिती नाही → "जवळच्या कृषी केंद्राला विचारा किंवा 1800-180-1551 वर call करा"

## भाषा:
- नेहमी मराठीत उत्तर दे
- साध्या शब्दात — शेतकऱ्याला समजेल असे
- Bullet points वापर, paragraphs नको

शेतकऱ्याला वाटले पाहिजे की तो एका अनुभवी, जवळच्या माणसाशी बोलतोय."""

# ── Intent Detection Keywords ──────────────────────────────────────────────
DISEASE_WORDS = [
    "rog", "dag", "blight", "fungus", "karpa", "kida", "pest", "disease",
    "kirda", "piwla", "black", "pivla", "ali", "insect", "spray",
    "मरतंय", "सुकतंय", "वाकडं", "काळं", "तपकिरी", "गळतंय", "कुजतंय",
    "पिवळं", "पांढरं", "डाग", "छिद्र", "अळी", "किडा", "बुरशी",
    "marat", "sukhat", "vakat", "kharab", "chidra", "pivla",
    "galat", "kujat", "pane", "pale", "yellow", "white", "brown",
    "problem", "trouble", "kahi", "nahi", "hotat", "zalay"
]

FERTILIZER_WORDS = [
    "khad", "khata", "khate", "fertilizer", "urea", "npk", "poshan",
    "dap", "potash", "zinc", "boron", "nutrients", "khaychi",
    "वाढत", "लहान", "खत", "पोषण", "खुजा",
    "vadhat", "lahan", "khuja", "grow", "growth"
]

WATER_WORDS = [
    "pani", "paani", "irrigation", "thipak", "drip", "पाणी", "ओलावा",
    "olava", "sukka", "कोरडं", "korda"
]

SEASON_WORDS = [
    "june", "july", "august", "kharif", "rabi", "season", "konat",
    "konti", "ghyav", "lagvad", "pik", "लागवड", "पेरणी", "कधी",
    "lavaycha", "perni", "kadhi", "vegali", "vegala", "yogy"
]

SCHEME_WORDS = [
    "yojana", "scheme", "sarkar", "vima", "kisan", "subsidy",
    "loan", "karj", "paise", "anudaan", "योजना", "अनुदान", "विमा",
    "सरकार", "पैसे", "कर्ज"
]

def _get_context(question: str, farmer: dict) -> str:
    q = question.lower()
    crops = str(farmer.get("crops", [])).lower()
    parts = []

    if any(w in q for w in DISEASE_WORDS):
        if any(c in crops for c in ["onion", "kanda", "kandaa"]):
            parts.append(KNOWLEDGE["onion_disease"])
        if any(c in crops for c in ["tomato", "tamatar", "tomatar"]):
            parts.append(KNOWLEDGE["tomato_disease"])
        parts.append(KNOWLEDGE["pest_control"])

    if any(w in q for w in FERTILIZER_WORDS):
        if any(c in crops for c in ["onion", "kanda"]):
            parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in crops for c in ["tomato", "tamatar"]):
            parts.append(KNOWLEDGE["fertilizer_tomato"])

    if any(w in q for w in SEASON_WORDS):
        parts.append(KNOWLEDGE["seasonal_calendar"])

    if any(w in q for w in WATER_WORDS):
        parts.append(KNOWLEDGE["irrigation"])

    if any(w in q for w in SCHEME_WORDS):
        parts.append(KNOWLEDGE["government_schemes"])

    # Default fallback — always give crop context
    if not parts:
        if any(c in crops for c in ["onion", "kanda"]):
            parts.append(KNOWLEDGE["onion_disease"])
            parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in crops for c in ["tomato", "tamatar"]):
            parts.append(KNOWLEDGE["tomato_disease"])
            parts.append(KNOWLEDGE["fertilizer_tomato"])

    return "\n\n".join(parts)

# ── API Calls ──────────────────────────────────────────────────────────────
async def _cerebras_call(messages: list, max_tokens: int = 600) -> str:
    if not CEREBRAS_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
                json={"model": CEREBRAS_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.15}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Cerebras: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        log.error(f"Cerebras failed: {e}")
        return ""

async def _groq_call(messages: list, max_tokens: int = 600) -> str:
    if not GROQ_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.15}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Groq: {r.status_code}")
            return ""
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return ""

async def farming_answer(question: str, farmer: dict, history: list = None) -> str:
    if not CEREBRAS_API_KEY and not GROQ_API_KEY:
        return "❌ सेवा सध्या उपलब्ध नाही. थोड्या वेळाने विचारा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")
        context = _get_context(question, farmer)

        messages = [{"role": "system", "content": SYSTEM}]

        if history:
            for h in history[-6:]:
                if h.get("user_message") and h["user_message"] not in ["[IMAGE]", "[VOICE]"]:
                    messages.append({"role": "user", "content": h["user_message"]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"]})

        user_content = f"शेतकरी: {city}, {district} | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ माहिती:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"
        messages.append({"role": "user", "content": user_content})

        ans = await _cerebras_call(messages, 600)
        if not ans:
            log.warning("Cerebras failed → Groq fallback")
            ans = await _groq_call(messages, 600)
        if not ans:
            return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

        return ans

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    if not image_bytes:
        return "❌ फोटो मिळाला नाही. पुन्हा पाठवा. 📸"
    try:
        import io, base64
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB": img = img.convert("RGB")
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        context = KNOWLEDGE["onion_disease"] + "\n" + KNOWLEDGE["tomato_disease"] + "\n" + KNOWLEDGE["pest_control"]

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"""तू KrishiMitra आहेस — अनुभवी कृषी रोग तज्ञ.

संदर्भ:
{context}

फोटो नीट बघ आणि मराठीत सांग:

📸 फोटो विश्लेषण

संभाव्य समस्या: [नाव सांग]
विश्वास: उच्च / मध्यम / कमी

📌 दिसणारी लक्षणे:
- [काय दिसतं ते सांग]

✅ पुढील उपाय:
- औषध: [brand name सहित]
- dose: 15 लिटर पंपाला [किती]
- कधी फवारायचे: [वेळ]

⚠️ काळजी:
- [महत्त्वाची सूचना]

शेतकरी {crops} घेतो. {f'शेतकरी म्हणतो: {caption}' if caption else ''}
फोटो नीट दिसत नसेल → "अधिक जवळून, प्रकाशात फोटो पाठवा" सांग."""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    "max_tokens": 500,
                    "temperature": 0.1
                }
            )
        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            return f"{d}\n\n📞 _कृषी हेल्पलाइन: 1800-180-1551 (मोफत)_"
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": ["onion", "tomato"], "city": "Pune", "district": "Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    if not GROQ_API_KEY or not audio_bytes: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                data={"model": "whisper-large-v3", "language": "mr", "response_format": "text"}
            )
            if r.status_code == 200: return r.text.strip()
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
