import logging
import httpx
from app.config import GROQ_API_KEY

log = logging.getLogger(__name__)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

KNOWLEDGE = {
    "onion_disease": """कांदा रोग:
• करपा (Purple Blotch): Iprodione 2g/L + Mancozeb 2g/L, सकाळी फवारा
• फुलकिडे (Thrips): Fipronil 1.5ml/L, 7 दिवसांनी पुन्हा
• मर रोग: Chlorothalonil 2g/L
• मूळकूज: Metalaxyl 2g/L ड्रेंचिंग""",
    "tomato_disease": """टोमॅटो रोग:
• करपा (Early Blight): Mancozeb 2.5g/L
• उशिरा करपा: Metalaxyl+Mancozeb 2.5g/L
• फळ पोखरणारी अळी: Emamectin 0.4g/L
• पांढरी माशी: Imidacloprid 0.3ml/L""",
    "fertilizer_onion": """कांदा खत:
• लागवड: DAP 150kg/acre + Potash 50kg/acre
• 15 दिवस: Urea 30kg/acre
• 30 दिवस: 19:19:19 @ 5g/L फवारणी
• 45 दिवस: Potash 25kg/acre""",
    "fertilizer_tomato": """टोमॅटो खत:
• लागवड: FYM 4 टन + DAP 100kg/acre
• 30 दिवस: 13:40:13 @ 5g/L फवारणी
• फळधारणा: Calcium Nitrate 3g/L""",
}

SYSTEM = """तू KrishiMitra आहेस — Maharashtra मधील शेतकऱ्यांचा जवळचा मित्र.

सगळ्यात महत्त्वाचे नियम:
1. Conversation history बघ — farmer काय बोलत होता ते लक्षात ठेव
2. "photo nahi", "nako", "nahi re", "dis nai" — हे सगळे "नाही" चे प्रकार आहेत — समजून घे
3. Farmer ने नकार दिला → symptoms विचार, मदत कर
4. Generic welcome message परत देऊ नकोस
5. छोटे उत्तर — 3-4 lines max
6. साधी मराठी — गावरान style

Conversation examples:
Farmer: "rog upay sanga"
तू: "📷 फोटो पाठवा — नक्की सांगतो"
Farmer: "photo nahi" / "nako" / "nahi re"
तू: "ठीक आहे 🙏 मग सांग — पाने पिवळी आहेत का तपकिरी? डाग कुठे आहेत?"

Farmer: "kandyala problem ahe"
तू: "काय होतंय कांद्याला? पाने वाळतायत का? रंग बदलतोय का?"

कधीही:
❌ Welcome message परत देऊ नकोस
❌ "मला आनंद आहे" बोलू नकोस  
❌ Guess करून चुकीचे dosage देऊ नकोस
✅ Context बघून natural बोल
✅ Follow-up विचार"""

def _get_context(question: str, farmer: dict) -> str:
    q = question.lower()
    crops = str(farmer.get("crops", [])).lower()
    parts = []
    if any(w in q for w in ["rog","dag","piwla","kirda","disease","blight","fungus","karpa"]):
        if any(c in crops for c in ["onion","kanda"]):
            parts.append(KNOWLEDGE["onion_disease"])
        if any(c in crops for c in ["tomato","tamatar"]):
            parts.append(KNOWLEDGE["tomato_disease"])
    if any(w in q for w in ["khata","khate","fertilizer","urea","npk","poshan"]):
        if any(c in crops for c in ["onion","kanda"]):
            parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in crops for c in ["tomato","tamatar"]):
            parts.append(KNOWLEDGE["fertilizer_tomato"])
    return "\n\n".join(parts)

async def _groq_call(messages: list, max_tokens: int = 250) -> str:
    if not GROQ_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Groq: {r.status_code}")
            return ""
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return ""

async def farming_answer(question: str, farmer: dict, history: list = None) -> str:
    if not GROQ_API_KEY:
        return "❌ सेवा सध्या उपलब्ध नाही. थोड्या वेळाने विचारा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        context = _get_context(question, farmer)

        # Messages list build karo
        messages = [{"role": "system", "content": SYSTEM}]

        # Conversation history inject karo — AI la memory milel
        if history:
            for h in history[-3:]:  # last 3 messages
                if h.get("user_message") and h["user_message"] != "[IMAGE]":
                    messages.append({"role": "user", "content": h["user_message"]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"]})

        # Current question with context
        user_content = f"शेतकरी: {city} | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"

        messages.append({"role": "user", "content": user_content})

        ans = await _groq_call(messages, 250)
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
        crops = ", ".join(farmer.get("crops", ["onion","tomato"]))
        context = KNOWLEDGE["onion_disease"] + "\n" + KNOWLEDGE["tomato_disease"]

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"""{SYSTEM}

संदर्भ माहिती:
{context}

फोटो पाहून सांग — साध्या मराठीत:
🌿 पीक कोणते?
🦠 रोग काय?
💊 उपाय — exact dosage
⚡ तातडी किती?

शेतकरी {crops} घेतो. {f'Note: {caption}' if caption else ''}"""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
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
    return await farming_answer(query, {"crops":["onion","tomato"],"city":"Pune","district":"Pune"})

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
