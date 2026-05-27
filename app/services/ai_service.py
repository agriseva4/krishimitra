import logging
import httpx
from app.config import GROQ_API_KEY

log = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM = """Tu KrishiMitra aahe — Maharashtra madhe Onion ani Tomato shetkaryansathi expert AI sahayak.

Tu SWATAH detect karshil farmer kaay vicharatoy:
- Mandi bhav / market price → Real market rates sang
- Havaman → Weather forecast + practical advice
- Pik rog / disease → Specific treatment sang
- Khate / fertilizer → Exact dosage sang
- Sarkar yojana → Scheme details sang
- Koni pn question → Tya topic var answer

NIYAM:
1. SAMPURN MARATHI madhe uttar dya — ek pn English word nahi
2. Specific dosage MANDATORY: "Mancozeb 2g/L"
3. Organic upay pehle, mag chemical
4. Pakke mahit nahi tar "कृषी सेवकाला विचारा" sang
5. Pune district + Maharashtra specific
6. WhatsApp format: *bold*, bullet points
7. Max 400 words — practical, direct"""

async def _groq(messages: list, max_tokens: int = 500) -> str:
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
                    "temperature": 0.2
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
        return "❌ *AI सेवा सध्या उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")

        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"""शेतकरी माहिती:
• ठिकाण: {city}, {district}, Maharashtra
• पिके: {crops}

प्रश्न: {question}

संपूर्ण मराठीत practical उत्तर द्या:"""}
        ]

        ans = await _groq(messages, 500)
        if not ans:
            return "❌ *AI सध्या व्यस्त आहे.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"

        return f"🌾 *KrishiMitra उत्तर:*\n\n{ans}\n\n━━━━━━━━━━━━\n📞 _किसान हेल्पलाइन: 1800-180-1551 (मोफत)_"

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ *AI सध्या व्यस्त आहे.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    if not image_bytes:
        return "❌ *फोटो मिळाला नाही.*\nकृपया स्पष्ट फोटो पुन्हा पाठवा. 📸"
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

        # Groq vision support
        if not GROQ_API_KEY:
            return "❌ *AI सेवा उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा पाठवा. 🙏"

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
                                "text": f"""तू Maharashtra कृषी रोग निदान Expert आहेस.
फोटो पाहून संपूर्ण मराठीत सांग:

🌿 *पिकाचे नाव:*
🦠 *रोगाचे नाव:*
✅ *विश्वास:* जास्त / मध्यम / कमी
👁️ *लक्षणे:*

💊 *उपाय:*
• सेंद्रिय: (specific + कसे वापरायचे)
• रासायनिक: (exact product + dosage g/L)
• फवारणी वेळ:

🛡️ *प्रतिबंधक उपाय:*
⚡ *तातडी:* लगेच करा / २-३ दिवस / निरीक्षण करा

शेतकरी {crops} घेतो. {f'टीप: {caption}' if caption else ''}"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                            }
                        ]
                    }],
                    "max_tokens": 600,
                    "temperature": 0.2
                }
            )

        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            suffix = "\n\n━━━━━━━━━━━━\n"
            if any(w in d.lower() for w in ["कमी", "unclear", "नक्की नाही"]):
                suffix += "⚠️ *AI ला नक्की सांगता येत नाही — तज्ञाला दाखवा!*\n📞 *1800-180-1551*"
            else:
                suffix += "⚠️ _AI निदान आहे — कृषी सेवकाकडून confirm करा._\n📞 _1800-180-1551_"
            return "🔬 *पीक रोग निदान — KrishiMitra*\n\n" + d + suffix
        else:
            log.error(f"Vision error: {r.status_code}")
            return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"

    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": ["onion", "tomato"], "city": "Pune", "district": "Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    if not GROQ_API_KEY or not audio_bytes:
        return ""
    try:
        import io
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
