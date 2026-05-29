import logging
import httpx
from app.config import GROQ_API_KEY

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM = """तू KrishiMitra आहेस — Maharashtra मधील शेतकऱ्यांचा विश्वासू मित्र आणि कृषी सल्लागार.

तू कसा बोलतोस:
- साधी, सोपी मराठी — गावातल्या माणसासारखी
- छोटे, practical उत्तरे — लांब paragraphs नाही
- आपुलकीने, मनापासून — robot सारखे नाही
- शेतकऱ्याची भावना समजून घे

उत्तर देताना:
- Marathi, Hinglish, spelling चुका — सगळे समजतात, judge करू नकोस
- चुकीचे उत्तर देण्यापेक्षा follow-up question विचार
- पीक रोग विचारले → फोटो माग
- हवामान विचारले → practical farming action सांग
- मंडई भाव → location mention कर
- नक्की माहित नाही → "कृषी सेवकाला विचारा" सांग

उत्तराचा style:
✅ "हो 🙏 उद्या पावसाची शक्यता आहे 🌧️ फवारणी आजच करा."
✅ "कांद्याला आत्ता Mancozeb 2g/L फवारा — सकाळी लवकर."
✅ "फोटो पाठवा 📷 मग नक्की सांगतो काय झालंय."

❌ असे बोलू नकोस:
- "मला आनंद आहे की आपण विचारले"
- "कृपया खालील माहिती पहा"
- "AI च्या मर्यादेमुळे..."
- लांब paragraphs
- कठीण technical शब्द

नेहमी लक्षात ठेव:
- तू customer support नाहीस
- तू AI chatbot नाहीस  
- तू शेतकऱ्याचा जवळचा मित्र आहेस
- Pune, Maharashtra specific advice दे
- Onion + Tomato specialist आहेस"""

async def _groq(messages: list, max_tokens: int = 300) -> str:
    if not GROQ_API_KEY:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3
                }
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Groq error: {r.status_code} — {r.text[:200]}")
            return ""
    except Exception as e:
        log.error(f"Groq call failed: {e}")
        return ""

async def farming_answer(question: str, farmer: dict) -> str:
    if not GROQ_API_KEY:
        return "❌ *AI सेवा सध्या उपलब्ध नाही.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"शेतकरी: {city}, {district} | पिके: {crops}\n\nप्रश्न: {question}"}
        ]

        ans = await _groq(messages, 300)
        if not ans:
            return "❌ *थोडी अडचण आली.*\nपुन्हा विचारा. 🙏"

        return ans

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ *थोडी अडचण आली.*\nपुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    if not image_bytes:
        return "❌ *फोटो मिळाला नाही.*\nपुन्हा पाठवा. 📸"
    try:
        import io, base64
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))

        if not GROQ_API_KEY:
            return "❌ *AI सेवा उपलब्ध नाही.*\nथोड्या वेळाने पुन्हा पाठवा. 🙏"

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""{SYSTEM}

फोटो पाहून सांग — साध्या मराठीत, शेतकऱ्याला समजेल असे:

🌿 पीक: कोणते?
🦠 रोग: नक्की काय?
👁️ लक्षणे: काय दिसतंय?
💊 उपाय: काय करायचं? (exact dosage सांग)
⚡ तातडी: लगेच करा / 2-3 दिवस वेळ आहे?

शेतकरी {crops} घेतो. {f'Note: {caption}' if caption else ''}
नक्की माहित नाही तर सरळ सांग."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                            }
                        ]
                    }],
                    "max_tokens": 400,
                    "temperature": 0.2
                }
            )

        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            return f"🔬 *पीक रोग निदान:*\n\n{d}\n\n━━━━━━━━━━━━\n📞 _1800-180-1551 (मोफत)_"
        else:
            log.error(f"Vision error: {r.status_code}")
            return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"

    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": ["onion", "tomato"], "city": "Pune", "district": "Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    if not GROQ_API_KEY or not audio_bytes:
        return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                data={
                    "model": "whisper-large-v3",
                    "language": "mr",
                    "response_format": "text"
                }
            )
            if r.status_code == 200:
                text = r.text.strip()
                log.info(f"Voice transcribed: {text[:50]}")
                return text
            log.error(f"Whisper error: {r.status_code}")
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
