import logging
import httpx
from app.config import GROQ_API_KEY

log = logging.getLogger(__name__)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

# ── Agriculture Knowledge Base (hardcoded — no RAG needed) ──────────────────
KNOWLEDGE = {
    "onion_disease": """
कांदा रोग माहिती:
• करपा (Purple Blotch): Iprodione 2g/L + Mancozeb 2g/L, सकाळी फवारा
• फुलकिडे (Thrips): Fipronil 1.5ml/L, 7 दिवसांनी पुन्हा
• मर रोग (Stemphylium): Chlorothalonil 2g/L
• कांदा माशी: Chlorpyrifos 2ml/L जमिनीत
• मूळकूज: Metalaxyl 2g/L ड्रेंचिंग
""",
    "tomato_disease": """
टोमॅटो रोग माहिती:
• करपा (Early Blight): Mancozeb 2.5g/L, 10 दिवसांनी पुन्हा
• उशिरा करपा (Late Blight): Metalaxyl+Mancozeb 2.5g/L
• फळ पोखरणारी अळी: Emamectin 0.4g/L
• पांढरी माशी: Imidacloprid 0.3ml/L
• विषाणू रोग: रोगी झाडे उपटा, पांढरी माशी नियंत्रण
""",
    "fertilizer_onion": """
कांदा खत वेळापत्रक:
• लागवड: DAP 150kg/acre + Potash 50kg/acre
• 15 दिवस: Urea 30kg/acre
• 30 दिवस: 19:19:19 @ 5g/L फवारणी
• 45 दिवस: Potash 25kg/acre
• फुलोरा: NPK बंद करा
""",
    "fertilizer_tomato": """
टोमॅटो खत वेळापत्रक:
• लागवड: FYM 4 टन + DAP 100kg/acre
• 15 दिवस: Urea 25kg/acre
• 30 दिवस: 13:40:13 @ 5g/L फवारणी
• फळधारणा: Calcium Nitrate 3g/L
• पक्वता: Potash 50kg/acre
""",
    "weather_farming": """
हवामान शेती सल्ला:
• पाऊस > 10mm: फवारणी करू नका, निचरा तपासा
• तापमान > 38°C: सकाळी पाणी, शेडनेट वापरा
• आर्द्रता > 80%: बुरशी रोग शक्य, preventive फवारणी
• वारा > 8m/s: फवारणी करू नका
• थंडी < 15°C: टोमॅटो संरक्षण, पाणी कमी करा
""",
    "mandi_guide": """
मंडई भाव माहिती:
• पुणे APMC: 020-24261756
• लासलगाव APMC: 02550-251054
• कांदा season: Oct-Mar उत्तम भाव
• टोमॅटो season: Nov-Feb उत्तम भाव
• eNAM portal: enam.gov.in
"""
}

def _get_context(question: str, farmer: dict) -> str:
    """Question नुसार relevant knowledge inject कर"""
    q = question.lower()
    context_parts = []

    # Crop specific context
    crops = farmer.get("crops", ["onion", "tomato"])

    if any(w in q for w in ["रोग","dag","daga","piwla","piwale","kirda","kida","kire","disease","rog","karpa","fungus","blight"]):
        if any(c in str(crops).lower() for c in ["onion","kandya","kanda"]):
            context_parts.append(KNOWLEDGE["onion_disease"])
        if any(c in str(crops).lower() for c in ["tomato","tamatar"]):
            context_parts.append(KNOWLEDGE["tomato_disease"])

    if any(w in q for w in ["khata","khate","fertilizer","urea","dap","npk","potash","poshan","nutrients"]):
        if any(c in str(crops).lower() for c in ["onion","kandya","kanda"]):
            context_parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in str(crops).lower() for c in ["tomato","tamatar"]):
            context_parts.append(KNOWLEDGE["fertilizer_tomato"])

    if any(w in q for w in ["paus","rain","havaman","weather","oon","thand","vara"]):
        context_parts.append(KNOWLEDGE["weather_farming"])

    if any(w in q for w in ["bhav","rate","mandi","market","price","किंमत"]):
        context_parts.append(KNOWLEDGE["mandi_guide"])

    return "\n".join(context_parts) if context_parts else ""

SYSTEM = """तू KrishiMitra आहेस — Maharashtra मधील शेतकऱ्यांचा विश्वासू मित्र.

बोलण्याची पद्धत:
- साधी गावरान मराठी — शेतकरी समजेल अशी
- छोटे उत्तर — 3-5 lines maximum
- आपुलकीने बोल — robot नाही
- Emoji वापर — 🌿 🧅 🍅 💧 ⚡

नियम:
1. Context मध्ये दिलेली माहितीच वापर
2. Dosage EXACT सांग — guess करू नकोस
3. नक्की माहित नाही → "फोटो पाठवा" किंवा "कृषी सेवकाला विचारा"
4. चुकीचे उत्तर देण्यापेक्षा follow-up विचार

उत्तराचे examples:
✅ "कांद्याला करपा दिसतोय 🍂 Mancozeb 2g/L सकाळी फवारा."
✅ "फोटो पाठवा 📷 मग नक्की सांगतो."
✅ "आज पाऊस येणार 🌧️ फवारणी उद्यावर ठेवा."
❌ "मला आनंद आहे की आपण विचारले..."
❌ लांब paragraphs"""

async def _groq(messages: list, max_tokens: int = 250) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Groq: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return ""

async def farming_answer(question: str, farmer: dict) -> str:
    if not GROQ_API_KEY:
        return "❌ सेवा सध्या उपलब्ध नाही. थोड्या वेळाने विचारा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")

        # Relevant context inject karo
        context = _get_context(question, farmer)

        user_msg = f"शेतकरी: {city}, {district} | पिके: {crops}"
        if context:
            user_msg += f"\n\nसंदर्भ माहिती:\n{context}"
        user_msg += f"\n\nप्रश्न: {question}"

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg}
        ]

        ans = await _groq(messages, 250)
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
        if img.width > 1024 or img.height > 1024: img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))

        # Disease context inject karo
        context = KNOWLEDGE["onion_disease"] + "\n" + KNOWLEDGE["tomato_disease"]

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"""{SYSTEM}

संदर्भ माहिती:
{context}

फोटो पाहून सांग — साध्या मराठीत:
🌿 पीक: कोणते?
🦠 रोग: काय?
💊 उपाय: exact dosage सांग
⚡ तातडी: लगेच / 2-3 दिवस?

शेतकरी {crops} घेतो. {f'Note: {caption}' if caption else ''}
Context मधील माहितीच वापर — guess करू नकोस."""},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }],
                    "max_tokens": 350,
                    "temperature": 0.1
                }
            )
        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            return f"🔬 *पीक रोग निदान:*\n\n{d}\n\n📞 _1800-180-1551 (मोफत)_"
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": ["onion","tomato"], "city":"Pune", "district":"Pune"})

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
            if r.status_code == 200:
                return r.text.strip()
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
