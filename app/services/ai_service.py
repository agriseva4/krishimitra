import logging
import httpx
from app.config import GROQ_API_KEY, CEREBRAS_API_KEY

log = logging.getLogger(__name__)

GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
GROQ_MODEL    = "llama-3.1-8b-instant"
CEREBRAS_MODEL = "llama-3.3-70b"

# ── Agriculture Knowledge Base ─────────────────────────────────────────────
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
• पांढरी माशी: Imidacloprid 0.3ml/L
• काळे डाग → Alternaria Blight: Mancozeb 2.5g/L + Copper Oxychloride 2g/L""",
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

तू Llama 3.3 70B आहेस — खूप smart, accurate आणि fast!

बोलण्याची पद्धत:
- साधी गावरान मराठी — शेतकरी समजेल अशी
- छोटे उत्तर — 3-5 lines maximum
- आपुलकीने बोल — robot नाही
- Conversation history लक्षात ठेव

नियम:
1. Context मधील माहिती वापर — guess करू नकोस
2. रोग विचारले → symptoms विचार किंवा फोटो माग
3. Dosage EXACT सांग — context मधून
4. नक्की माहित नाही → "कृषी सेवकाला विचारा"
5. Short replies — 3-5 lines max

Examples:
✅ "कांद्याला करपा दिसतोय 🍂 Mancozeb 2g/L सकाळी फवारा."
✅ "📷 फोटो पाठवा — नक्की सांगतो."
✅ "आज पाऊस येणार 🌧️ फवारणी उद्यावर ठेवा."
❌ लांब paragraphs
❌ "मला आनंद आहे..."
❌ Generic answers"""

def _get_context(question: str, farmer: dict) -> str:
    q = question.lower()
    crops = str(farmer.get("crops", [])).lower()
    parts = []
    if any(w in q for w in ["rog","dag","piwla","kirda","disease","blight","fungus","karpa","kida"]):
        if any(c in crops for c in ["onion","kanda"]): parts.append(KNOWLEDGE["onion_disease"])
        if any(c in crops for c in ["tomato","tamatar"]): parts.append(KNOWLEDGE["tomato_disease"])
    if any(w in q for w in ["khata","khate","fertilizer","urea","npk","poshan","khad"]):
        if any(c in crops for c in ["onion","kanda"]): parts.append(KNOWLEDGE["fertilizer_onion"])
        if any(c in crops for c in ["tomato","tamatar"]): parts.append(KNOWLEDGE["fertilizer_tomato"])
    return "\n\n".join(parts)

async def _cerebras_call(messages: list, max_tokens: int = 300) -> str:
    """Cerebras 70B — Text Q&A sathi"""
    if not CEREBRAS_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                CEREBRAS_URL,
                headers={
                    "Authorization": f"Bearer {CEREBRAS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": CEREBRAS_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2
                }
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Cerebras: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        log.error(f"Cerebras failed: {e}")
        return ""

async def _groq_call(messages: list, max_tokens: int = 300) -> str:
    """Groq — Fallback sathi"""
    if not GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2
                }
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

        # Conversation history inject
        if history:
            for h in history[-3:]:
                if h.get("user_message") and h["user_message"] not in ["[IMAGE]", "[VOICE]"]:
                    messages.append({"role": "user", "content": h["user_message"]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"]})

        user_content = f"शेतकरी: {city}, {district} | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"
        messages.append({"role": "user", "content": user_content})

        # Cerebras try karo — nahi zala tar Groq fallback
        ans = await _cerebras_call(messages, 300)
        if not ans:
            log.warning("Cerebras failed, using Groq fallback")
            ans = await _groq_call(messages, 300)
        if not ans:
            return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

        return ans

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    """Photo sathi Groq Vision — Cerebras la image support nahi"""
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
    return await farming_answer(query, {"crops": ["onion","tomato"], "city":"Pune", "district":"Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    """Voice sathi Groq Whisper — Cerebras la audio support nahi"""
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
