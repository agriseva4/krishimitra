import logging
import google.generativeai as genai
from app.config import GEMINI_API_KEY

log = logging.getLogger(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    log.info("✅ Gemini configured!")
else:
    log.error("❌ GEMINI_API_KEY missing!")

SYSTEM = """Tu KrishiMitra aahe — Maharashtra madhe Onion ani Tomato shetkaryansathi expert AI sahayak.

Tu SWATAH detect karshil farmer kaay vicharatoy:
- Mandi bhav / market price vicharla → Real market rates sang (Pune, Lasalgaon, Nashik etc.)
- Havaman vicharla → Weather forecast sang practical advice sobat  
- Pik rog / disease vicharla → Specific treatment sang
- Khate / fertilizer vicharla → Exact dosage sang
- Sarkar yojana vicharla → Scheme details sang
- Koni pn question vicharla → Tya topic var answer dya

NIYAM:
1. SAMPURN MARATHI madhe uttar dya — ek pn English word nahi
2. Specific dosage MANDATORY: "Mancozeb 2g/L"
3. Organic upay pehle, mag chemical
4. Pakke mahit nahi tar "कृषी सेवकाला विचारा" sang
5. Pune district + Maharashtra specific
6. WhatsApp format: *bold*, bullet points •
7. Max 400 words
8. Practical, direct — shetkari samjel ase

MARATHI SHABD VAPRA:
- Market/Mandi → मंडई / बाजार
- Rate/Price → भाव / किंमत  
- Farmer → शेतकरी
- Crop → पीक
- Disease → रोग
- Fertilizer → खत
- Weather → हवामान"""

async def farming_answer(question: str, farmer: dict) -> str:
    if not GEMINI_API_KEY:
        return "❌ *AI सेवा सध्या उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")

        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"""{SYSTEM}

शेतकरी माहिती:
• ठिकाण: {city}, {district}, Maharashtra
• पिके: {crops}

प्रश्न: {question}

संपूर्ण मराठीत practical उत्तर द्या:"""

        r = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=500
            )
        )
        ans = r.text.strip()
        return f"🌾 *KrishiMitra उत्तर:*\n\n{ans}\n\n━━━━━━━━━━━━\n📞 _किसान हेल्पलाइन: 1800-180-1551 (मोफत)_"
    except Exception as e:
        log.error(f"farming_answer error: {e}")
        return "❌ *AI सध्या व्यस्त आहे.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    if not GEMINI_API_KEY:
        return "❌ *AI सेवा उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा पाठवा. 🙏"
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
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"""तू Maharashtra कृषी रोग निदान Expert आहेस.
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

शेतकरी {crops} घेतो. {f'टीप: {caption}' if caption else ''}
नक्की माहित नाही तर तज्ञाला दाखवा सांग."""

        r = model.generate_content(
            [prompt, {"mime_type": "image/jpeg", "data": b64}]
        )
        d = r.text.strip()
        suffix = "\n\n━━━━━━━━━━━━\n"
        if any(w in d.lower() for w in ["कमी", "unclear", "नक्की नाही"]):
            suffix += "⚠️ *AI ला नक्की सांगता येत नाही — तज्ञाला दाखवा!*\n📞 *1800-180-1551*"
        else:
            suffix += "⚠️ _AI निदान आहे — कृषी सेवकाकडून confirm करा._\n📞 _1800-180-1551_"
        return "🔬 *पीक रोग निदान — KrishiMitra*\n\n" + d + suffix
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": ["onion", "tomato"], "city": "Pune", "district": "Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    if not GEMINI_API_KEY or not audio_bytes:
        return ""
    try:
        import base64
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        b64 = base64.b64encode(audio_bytes).decode()
        prompt = """हे WhatsApp voice message आहे.
यातील बोलणे EXACTLY transcribe कर — Marathi, Hindi, या English मध्ये.
फक्त transcription दे, explanation नको.
नीट ऐकू येत नाही तर UNCLEAR लिही."""
        r = model.generate_content([
            prompt,
            {"mime_type": "audio/ogg", "data": b64}
        ])
        text = r.text.strip()
        if "UNCLEAR" in text or len(text) < 2:
            return ""
        return text
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
