import logging
from app.config import GEMINI_API_KEY

log = logging.getLogger(__name__)
_model = None

def get_model():
    global _model
    if _model: return _model
    if not GEMINI_API_KEY or GEMINI_API_KEY == "PASTE_HERE":
        log.error("GEMINI_API_KEY missing!")
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        for m in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]:
            try:
                _model = genai.GenerativeModel(m)
                log.info(f"✅ Gemini connected: {m}")
                return _model
            except Exception:
                continue
        log.error("No Gemini model available!")
        return None
    except Exception as e:
        log.error(f"Gemini init: {e}")
        return None

def _cfg(temp=0.2, tokens=500):
    try:
        import google.generativeai as genai
        return genai.types.GenerationConfig(temperature=temp, max_output_tokens=tokens)
    except:
        return None

SYSTEM = """Tu KrishiMitra aahe — Maharashtra, Pune madhe Onion ani Tomato shetkaryansathi expert AI sahayak.

MUKHYA NIYAM:
1. FAKT verified mahiti sang — kabhi andaaj lau naka
2. SPECIFIC dosage MANDATORY: "Mancozeb 2g/L"
3. Saral Marathi — shetkari samjel ase lihit raha
4. Source cite kar: "ICAR nusar" / "Krushi Vibhag nusar"
5. Onion (Kandya) + Tomato specialist
6. Organic upay PEHLE, mag chemical
7. Pakke mahit nahi → "Krushi sevak la vicharaa" sang
8. Maharashtra seasonal calendar follow kar
9. Pune district specific advice dya

FORMAT:
- WhatsApp Bold: *text*
- Bullet: •
- Max 400 words
- Practical, direct steps"""

async def voice_to_text(audio_bytes: bytes) -> str:
    """Voice message → Marathi text convert"""
    m = get_model()
    if not m: return ""
    if not audio_bytes: return ""
    try:
        import base64
        b64 = base64.b64encode(audio_bytes).decode()
        prompt = """He WhatsApp voice message ahe. 
Yatil bolne EXACTLY transcribe kar — Marathi, Hindi, ya English madhe jo bolala ahe.
Fakt transcription dya, kahi explanation nako.
Jar nit aiku yet nahi tar 'UNCLEAR' lihia."""
        r = m.generate_content([
            prompt,
            {"mime_type": "audio/ogg", "data": b64}
        ])
        text = r.text.strip()
        if "UNCLEAR" in text or len(text) < 2:
            return ""
        log.info(f"Voice transcribed: {text[:50]}")
        return text
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""

async def farming_answer(question: str, farmer: dict) -> str:
    m = get_model()
    if not m: return "❌ *AI सेवा सध्या उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा प्रयत्न करा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        prompt = f"""{SYSTEM}

Shetkari Info:
- Location: {city}, Maharashtra
- Crops: {crops}
- Language: Marathi preferred

Prashn: {question}

Detailed Marathi madhe practical uttar dya:"""
        r = m.generate_content(prompt, generation_config=_cfg(0.2, 500))
        ans = r.text.strip()
        uncertain = ["mala mahit nahi", "i don't know", "not sure", "pakke nahi", "uncertain", "cannot say"]
        if any(u in ans.lower() for u in uncertain):
            return _expert()
        return f"🌾 *KrishiMitra उत्तर:*\n\n{ans}\n\n━━━━━━━━━━━━\n⚠️ _निर्णय घेण्यापूर्वी कृषी सेवकाला भेट द्या._\n📞 _किसान हेल्पलाइन: 1800-180-1551 (मोफत)_"
    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ *AI सेवा सध्या व्यस्त आहे.*\nथोड्या वेळाने पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    m = get_model()
    if not m: return "❌ *AI सेवा उपलब्ध नाही.*\nकृपया थोड्या वेळाने पुन्हा पाठवा. 🙏"
    if not image_bytes: return "❌ *फोटो मिळाला नाही.*\nकृपया स्पष्ट फोटो पुन्हा पाठवा. 📸"
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
        prompt = f"""Tu Maharashtra Krushi Rog Nidan Expert aahe.
Photo paahun MARATHI madhe exact sangaa:

🌿 *पिकाचे नाव:* (कोणते पीक आहे?)
🦠 *रोगाचे नाव:* (specific disease name)
✅ *विश्वास:* जास्त / मध्यम / कमी
👁️ *लक्षणे:* (नक्की काय दिसत आहे)

💊 *उपाय:*
- सेंद्रिय: (specific + कसे वापरायचे)
- रासायनिक: (exact product name + dosage g/L)
- फवारणी वेळ: (सकाळी/सायंकाळी/केव्हा नाही)

🛡️ *प्रतिबंधक:* (भविष्यात कसे वाचवायचे)
⚡ *तातडी:* लगेच करा / २-३ दिवस / निरीक्षण करा

Shetkari {crops} gheto. {f'Note: {caption}' if caption else ''}

MAHATVACHE: Pakke nahi tar 'तज्ञाला फोटो दाखवा' sang!"""
        r = m.generate_content([prompt, {"mime_type": "image/jpeg", "data": b64}])
        d = r.text.strip()
        low = any(w in d.lower() for w in ["low", "pakke nahi", "expert la", "unclear", "cannot"])
        prefix = "🔬 *पीक रोग निदान — KrishiMitra*\n\n"
        suffix = "\n\n━━━━━━━━━━━━\n"
        if low:
            suffix += "⚠️ *AI ला नक्की सांगता येत नाही — तज्ञाला दाखवा!*\n📞 *1800-180-1551* (मोफत, 24/7)"
        else:
            suffix += "⚠️ _AI निदान आहे — कृषी सेवकाकडून confirm करा._\n📞 _1800-180-1551 (मोफत)_"
        return prefix + d + suffix
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ *फोटो तपासता आला नाही.*\nस्वच्छ, प्रकाशात काढलेला फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    m = get_model()
    if not m: return _schemes_fallback()
    try:
        prompt = f"""Tu Maharashtra shetkari sarkar yojana expert aahe.

YOJANA DATABASE:
- PM-KISAN: ₹6,000/year (₹2K × 3) | pmkisan.gov.in | Helpline: 155261
- PMFBY Pik Vima: Kandya 2% premium, Tomato covered | Bank madhe apply
- Kisan Credit Card: ₹3L paryant, 4% vyajdar | Nazdikchi bank
- Drip/Sprinkler Subsidy: 55-65% off | Krushi Vibhag Karyalay
- Maharashtra Shetkari Sanman: ₹12,000/year | mahakrishidept.gov.in
- Soil Health Card: Free mati pareeksha | KVK Pune: 020-25695081
- eNAM: Online mandi better price | enam.gov.in

Prashn: {query}

Saral Marathi madhe uttar: relevant yojana, eligibility, apply kasa, helpline."""
        r = m.generate_content(prompt, generation_config=_cfg(0.1, 400))
        return f"🏛️ *सरकारी योजना — KrishiMitra*\n\n{r.text.strip()}\n\n━━━━━━━━━━━━\n📞 किसान हेल्पलाइन: *1800-180-1551* (मोफत)\n📞 PM-KISAN: *155261*"
    except Exception as e:
        log.error(f"scheme_info: {e}")
        return _schemes_fallback()

def _expert():
    return ("⚠️ *हा प्रश्न थोडा क्लिष्ट आहे*\n\n"
            "📞 *लगेच संपर्क करा:*\n"
            "• किसान कॉल सेंटर: *1800-180-1551* (मोफत, 24/7)\n"
            "• पुणे कृषी विभाग: 020-26130990\n"
            "• KVK पुणे: 020-25695081\n\n"
            "_KrishiMitra — तज्ञाकडे पाठवत आहे_ 🙏")

def _schemes_fallback():
    return ("🏛️ *मुख्य योजना:*\n\n"
            "1️⃣ *PM-KISAN* — ₹6,000/वर्ष\n   👉 pmkisan.gov.in | 155261\n\n"
            "2️⃣ *पीक विमा* — कांदा+टोमॅटो covered\n   👉 बँकेत अर्ज करा\n\n"
            "3️⃣ *KCC कर्ज* — ₹3L at 4%\n   👉 जवळची बँक\n\n"
            "4️⃣ *ठिबक अनुदान* — 55% सूट\n   👉 कृषी विभाग\n\n"
            "📞 *1800-180-1551* (मोफत)")
