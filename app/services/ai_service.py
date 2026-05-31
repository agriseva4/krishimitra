import logging
import httpx
from app.config import GROQ_API_KEY, CEREBRAS_API_KEY

log = logging.getLogger(__name__)

GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
GROQ_MODEL     = "llama-3.1-8b-instant"
CEREBRAS_MODEL = "llama-3.3-70b"

KNOWLEDGE = {
    "onion_disease": """कांदा रोग:
• करपा (Purple Blotch): Iprodione 2g/L + Mancozeb 2g/L, सकाळी फवारा
• फुलकिडे (Thrips): Fipronil 1.5ml/L, 7 दिवसांनी पुन्हा
• मर रोग (Stemphylium): Chlorothalonil 2g/L
• मूळकूज: Metalaxyl 2g/L ड्रेंचिंग
• प्रतिबंध: Copper Oxychloride 3g/L दर 10 दिवसांनी""",

    "tomato_disease": """टोमॅटो रोग:
• करपा (Early Blight): Mancozeb 2.5g/L, 10 दिवसांनी पुन्हा
• उशिरा करपा: Metalaxyl+Mancozeb 2.5g/L
• काळे डाग (Alternaria): Mancozeb 2.5g/L + Copper Oxychloride 2g/L
• फळ पोखरणारी अळी: Emamectin 0.4g/L संध्याकाळी
• पांढरी माशी: Imidacloprid 0.3ml/L
• विषाणू रोग: रोगी झाडे उपटा, पांढरी माशी नियंत्रण""",

    "fertilizer_onion": """कांदा खत:
• लागवड: FYM 4 टन/acre + DAP 150kg/acre + Potash 50kg/acre
• 15 दिवस: Urea 30kg/acre
• 30 दिवस: 19:19:19 @ 5g/L फवारणी
• 45 दिवस: Potash 25kg/acre
• फुलोरा: खत बंद""",

    "fertilizer_tomato": """टोमॅटो खत:
• लागवड: FYM 5 टन/acre + DAP 100kg/acre
• 15 दिवस: Urea 25kg/acre
• 30 दिवस: 13:40:13 @ 5g/L फवारणी
• फळधारणा: Calcium Nitrate 3g/L + Boron 1g/L
• पक्वता: Potash 50kg/acre""",

    "seasonal_calendar": """Maharashtra Seasonal Calendar:
Kharif (June-October): Soybean, Tur, Maize, Cotton, Bhendi, Kakdi, Dudhi
Rabi (October-March): Onion, Tomato, Wheat, Harbhara

June madhe yogya: Soybean, Tur, Maize, Cotton, Bhendi
June madhe onion/tomato lagvad nahi — July-August madhe ropvatika""",

    "pest_control": """किडे नियंत्रण:
• फुलकिडे: Fipronil 1.5ml/L
• मावा: Imidacloprid 0.3ml/L
• अळी: Emamectin 0.4g/L
• पांढरी माशी: Imidacloprid 0.3ml/L
• फवारणी: सकाळी 7-9 किंवा संध्याकाळी 5-7""",

    "irrigation": """पाणी व्यवस्थापन:
• कांदा: 7-10 दिवसांनी, काढणी 15 दिवस आधी बंद
• टोमॅटो: 4-5 दिवसांनी, नियमित
• उन्हाळ्यात: सकाळी लवकर
• ठिबक: 60-70% पाणी वाचते""",

    "government_schemes": """सरकारी योजना:
• PM-KISAN: ₹6,000/वर्ष | pmkisan.gov.in | 155261
• PMFBY पीक विमा: कांदा 2% premium | बँकेत अर्ज
• KCC कर्ज: ₹3L, 4% व्याज | जवळची बँक
• ठिबक अनुदान: 55-65% सूट | कृषी विभाग
• माती आरोग्य कार्ड: मोफत | KVK: 020-25695081""",
}

SYSTEM = """तू KrishiMitra AI आहेस — भारतातील शेतकऱ्यांसाठी मराठी कृषी सहाय्यक.

ध्येय: साध्या, practical आणि शेतकरी-मित्र मराठीत मार्गदर्शन करणे.

महत्त्वाचे:
- कधीही facts, pesticide doses, fertilizer recommendations शोधून काढू नकोस
- नक्की माहित नाही → follow-up विचार किंवा "कृषी सेवकाला विचारा" सांग
- "As an AI" किंवा "language model" असे कधीही बोलू नकोस

भाषा:
- नेहमी मराठीत उत्तर दे
- साधी शेतकरी-मित्र भाषा
- Bullet points वापर
- Robot सारखे बोलू नकोस
- Technical jargon टाळ

व्यक्तिमत्व:
- मित्रत्वाचे, आदरयुक्त, practical, direct
- अनुभवी कृषी सल्लागारासारखे बोल

रोग प्रश्न — आधी विचार:
- कोणते पीक?
- कोणती लक्षणे?
- पाने/फळ/खोड कुठे?
- किती दिवसांपासून?
- फोटो आहे का?

रोग उत्तर format:
🔍 संभाव्य समस्या
📌 दिसणारी लक्षणे
✅ काय करावे
⚠️ काळजी

फोटो format:
📸 फोटो विश्लेषण
संभाव्य समस्या:
विश्वास: उच्च/मध्यम/कमी
✅ पुढील उपाय

हवामान format:
🌦️ हवामान माहिती
🚜 शेतकरी सल्ला

मंडई format:
📈 बाजारभाव
पीक: | बाजार:
💡 सूचना

खत format — आधी समजून घे:
- पीक कोणते?
- Stage काय?
- लक्षणे काय?
नंतर:
🌱 समस्या
✅ संभाव्य उपाय
⚠️ काळजी

किडे format:
🐛 संभाव्य कीड
📌 लक्षणे
✅ नियंत्रण उपाय
⚠️ सूचना

Safety:
- "हे औषध नक्की काम करेल" असे कधीही नाही
- "याचा फायदा होऊ शकतो" असे सांग
- नक्की माहित नाही → "माझ्याकडे सध्या पुरेशी माहिती नाही"

Supported crops: Tomato, Onion, Potato, Brinjal, Chilli, Okra, Cabbage, Cauliflower, Cotton, Soybean, Sugarcane, Rice, Wheat, Maize, Tur, Gram, Grapes, Pomegranate, Banana, Mango, Orange आणि इतर सर्व

प्रत्येक उत्तर:
✔ मराठी ✔ Short ✔ Practical ✔ Easy ✔ Action-oriented

शेतकऱ्याला वाटले पाहिजे की तो एका अनुभवी कृषी सल्लागाराशी बोलत आहे."""

def _get_context(question: str, farmer: dict) -> str:
    q = question.lower()
    crops = str(farmer.get("crops", [])).lower()
    parts = []

    if any(w in q for w in ["rog","dag","piwla","kirda","disease","blight","fungus","karpa","kida","pest","ali","black","pivla"]):
        if any(c in crops for c in ["onion","kanda"]): parts.append(KNOWLEDGE["onion_disease"])
        if any(c in crops for c in ["tomato","tamatar"]): parts.append(KNOWLEDGE["tomato_disease"])
        parts.append(KNOWLEDGE["pest_control"])

    if any(w in q for w in ["khata","khate","fertilizer","urea","npk","poshan","khad"]):
        if any(c in crops for c in ["onion","kanda"]): parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in crops for c in ["tomato","tamatar"]): parts.append(KNOWLEDGE["fertilizer_tomato"])

    if any(w in q for w in ["june","july","kharif","rabi","season","konat","konti","ghyav","lagvad","pik"]):
        parts.append(KNOWLEDGE["seasonal_calendar"])

    if any(w in q for w in ["pani","irrigation","thipak","paani"]):
        parts.append(KNOWLEDGE["irrigation"])

    if any(w in q for w in ["yojana","scheme","sarkar","vima","kisan","subsidy","loan","karj"]):
        parts.append(KNOWLEDGE["government_schemes"])

    return "\n\n".join(parts)

async def _cerebras_call(messages: list, max_tokens: int = 500) -> str:
    if not CEREBRAS_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
                json={"model": CEREBRAS_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Cerebras: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        log.error(f"Cerebras failed: {e}")
        return ""

async def _groq_call(messages: list, max_tokens: int = 500) -> str:
    if not GROQ_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
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
            for h in history[-3:]:
                if h.get("user_message") and h["user_message"] not in ["[IMAGE]", "[VOICE]"]:
                    messages.append({"role": "user", "content": h["user_message"]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"]})

        user_content = f"शेतकरी: {city}, {district}, Maharashtra | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"
        messages.append({"role": "user", "content": user_content})

        ans = await _cerebras_call(messages, 500)
        if not ans:
            log.warning("Cerebras failed → Groq fallback")
            ans = await _groq_call(messages, 500)
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
                        {"type": "text", "text": f"""तू KrishiMitra AI आहेस — अनुभवी कृषी रोग निदान expert.

संदर्भ:
{context}

फोटो पाहून मराठीत सांग:

📸 फोटो विश्लेषण

संभाव्य समस्या:
विश्वास: उच्च / मध्यम / कमी
📌 दिसणारी लक्षणे:
✅ पुढील उपाय — exact dosage सहित
⚠️ काळजी:

शेतकरी {crops} घेतो. {f'टीप: {caption}' if caption else ''}
Context वापर — guess करू नकोस. नक्की नाही → "अधिक स्पष्ट फोटो पाठवा" सांग."""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    "max_tokens": 400,
                    "temperature": 0.1
                }
            )
        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            return f"{d}\n\n📞 _1800-180-1551 (मोफत)_"
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
            if r.status_code == 200: return r.text.strip()
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
