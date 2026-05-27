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

NIYAM:
1. FAKT Marathi madhe uttar dya — English words shaktoto nahi
2. Specific dosage sang: "Mancozeb 2g/L"
3. Organic upay pehle, mag chemical
4. Source: "ICAR nusar" / "Krushi Vibhag nusar"
5. Pakke mahit nahi tar "Krushi sevak la vicharaa" sang
6. Pune district + Maharashtra specific advice
7. WhatsApp format: *bold*, bullet points
8. Max 350 words — concise raha

TOPICS: pik rog, khate, havaman, mandi bhav, sarkar yojana, irrigation, seeds, kiti control"""

async def farming_answer(question: str, farmer: dict) -> str:
    if not GEMINI_API_KEY:
        return "❌ *AI सेवा सध्या उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"""{SYSTEM}

शेतकरी माहिती: {city}, Maharashtra | पिके: {crops}

प्रश्न: {question}

मराठीत practical उत्तर द्या:"""
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
फोटो पाहून मराठीत सांग:

🌿 *पिकाचे नाव:*
🦠 *रोगाचे नाव:*
✅ *विश्वास:* जास्त / मध्यम / कमी
👁️ *लक्षणे:*

💊 *उपाय:*
• सेंद्रिय: (specific + कसे वापरायचे)
• रासायनिक: (exact product + dosage)
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
    if not GEMINI_API_KEY:
        return _schemes_fallback()
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"""तू Maharashtra शेतकरी सरकार योजना expert आहेस.

योजना माहिती:
• PM-KISAN: ₹6,000/वर्ष | pmkisan.gov.in | 155261
• PMFBY पीक विमा: कांदा 2% premium | बँकेत अर्ज
• किसान क्रेडिट कार्ड: ₹3L, 4% व्याज | जवळची बँक
• ठिबक अनुदान: 55-65% सूट | कृषी विभाग
• Maharashtra शेतकरी सन्मान: ₹12,000/वर्ष
• माती आरोग्य कार्ड: मोफत | KVK Pune: 020-25695081

प्रश्न: {query}

मराठीत सांग: योजना, eligibility, कसे apply करायचे, helpline."""
        r = model.generate_content(prompt)
        return f"🏛️ *सरकारी योजना — KrishiMitra*\n\n{r.text.strip()}\n\n━━━━━━━━━━━━\n📞 किसान हेल्पलाइन: *1800-180-1551* (मोफत)\n📞 PM-KISAN: *155261*"
    except Exception as e:
        log.error(f"scheme_info: {e}")
        return _schemes_fallback()

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

def _schemes_fallback():
    return ("🏛️ *मुख्य योजना:*\n\n"
            "1️⃣ *PM-KISAN* — ₹6,000/वर्ष\n   👉 pmkisan.gov.in | 155261\n\n"
            "2️⃣ *पीक विमा* — कांदा+टोमॅटो covered\n   👉 बँकेत अर्ज करा\n\n"
            "3️⃣ *KCC कर्ज* — ₹3L at 4%\n   👉 जवळची बँक\n\n"
            "4️⃣ *ठिबक अनुदान* — 55% सूट\n   👉 कृषी विभाग\n\n"
            "📞 *1800-180-1551* (मोफत)")
