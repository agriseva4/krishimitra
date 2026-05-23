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

GEN_CFG = None

def _cfg(temp=0.2, tokens=500):
    try:
        import google.generativeai as genai
        return genai.types.GenerationConfig(temperature=temp, max_output_tokens=tokens)
    except:
        return None

SYSTEM = """Tu KrishiMitra aahe — Maharashtra, Pune madhe Onion ani Tomato shetkaryansathi expert AI sahayak.

MUKHYA NIYAM:
1. FAKT verified mahiti sang — kabhi andaaj lau naka
2. SPECIFIC dosage MANDATORY: "Mancozeb 2g/L" (thodi/jaas nako)
3. Saral Marathi — shetkari samjel ase lihit raha
4. Source cite kar: "ICAR nusar" / "Krushi Vibhag nusar"
5. Onion (Kandya) + Tomato specialist
6. Organic upay PEHLE, mag chemical
7. Pakke mahit nahi → "Krushi sevak la vicharaa" sang
8. Maharashtra seasonal calendar follow kar
9. Pune district specific advice dya

FORMAT:
• WhatsApp Bold: *text*
• Bullet: •
• Max 400 words
• Practical, direct steps"""

async def farming_answer(question: str, farmer: dict) -> str:
    m = get_model()
    if not m: return "❌ AI unavailable. GEMINI_API_KEY check kara."
    try:
        crops = ", ".join(farmer.get("crops", ["onion", "tomato"]))
        city = farmer.get("city", "Pune")
        prompt = f"""{SYSTEM}

Shetkari Info:
• Location: {city}, Maharashtra
• Crops: {crops}
• Language: Marathi preferred

Prashn: {question}

Detailed Marathi madhe practical uttar dya:"""
        r = m.generate_content(prompt, generation_config=_cfg(0.2, 500))
        ans = r.text.strip()
        uncertain = ["mala mahit nahi", "i don't know", "not sure", "pakke nahi", "uncertain", "cannot say"]
        if any(u in ans.lower() for u in uncertain):
            return _expert()
        return f"🌾 *KrishiMitra Uttar:*\n\n{ans}\n\n━━━━━━━━━━━━\n⚠️ _Nirnay ghenya pUrvi Krushi Sevak la bhet dya._\n📞 _Kisan Helpline: 1800-180-1551 (Free)_"
    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ AI thodi vel sathi unavailable. Parat prayatna kara. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    m = get_model()
    if not m: return "❌ AI unavailable."
    if not image_bytes: return "❌ Photo milali nahi. Parat pathva."
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

🌿 *Pikache Nav:* (konti pik ahe?)
🦠 *Rogache Nav:* (specific disease name)
✅ *Vishwas:* High / Medium / Low
👁️ *Lakshane:* (exactly kay disat ahe)

💊 *Upay:*
• Organic: (specific + kasa vapraaychaa)
• Chemical: (exact product name + dosage g/L)
• Spray timing: (subahi/sayan/keva nahi)

🛡️ *Pratibandhak:* (future madhe kasa vachavaayacha)
⚡ *Urgency:* Lagar kara / 2-3 din / Observe kara

Shetkari {crops} gheto. {f'Note: {caption}' if caption else ''}

MAHATVACHE: Pakke nahi tar "Expert la photo daakhva" sang — andaaj lau naka!"""
        r = m.generate_content([prompt, {"mime_type": "image/jpeg", "data": b64}])
        d = r.text.strip()
        low = any(w in d.lower() for w in ["low", "pakke nahi", "expert la", "unclear", "cannot"])
        prefix = "🔬 *Pik Rog Nidan — KrishiMitra*\n\n"
        suffix = "\n\n━━━━━━━━━━━━\n"
        if low:
            suffix += "⚠️ *AI la pakke sangta yet nahi — Expert la daakhva!*\n📞 *1800-180-1551* (Free, 24/7)"
        else:
            suffix += "⚠️ _AI nidan ahe — Krushi Sevak la confirm kara._\n📞 _1800-180-1551 (Free)_"
        return prefix + d + suffix
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ Photo process karta ali nahi.\nSaaf, prakashit photo pathva. 🙏"

async def scheme_info(query: str) -> str:
    m = get_model()
    if not m: return _schemes_fallback()
    try:
        prompt = f"""Tu Maharashtra shetkari sarkar yojana expert aahe.

YOJANA DATABASE:
• PM-KISAN: ₹6,000/year (₹2K × 3) | pmkisan.gov.in | Helpline: 155261
• PMFBY Pik Vima: Kandya 2% premium, Tomato covered | Bank madhe apply
• Kisan Credit Card: ₹3L paryant, 4% व्याजdar | Nazdikchi bank
• Drip/Sprinkler Subsidy: 55-65% off | Krushi Vibhag Karyalay
• Maharashtra Shetkari Sanman: ₹12,000/year | mahakrishidept.gov.in
• Soil Health Card: Free mati pareeksha | KVK Pune: 020-25695081
• eNAM: Online mandi better price | enam.gov.in

Prashn: {query}

Saral Marathi madhe uttar: relevant yojana, eligibility, apply kasa, helpline."""
        r = m.generate_content(prompt, generation_config=_cfg(0.1, 400))
        return f"🏛️ *Sarkar Yojana — KrishiMitra*\n\n{r.text.strip()}\n\n━━━━━━━━━━━━\n📞 Kisan Helpline: *1800-180-1551* (Free)\n📞 PM-KISAN: *155261*"
    except Exception as e:
        log.error(f"scheme_info: {e}")
        return _schemes_fallback()

def _expert():
    return ("⚠️ *Ha prashn thoda complex ahe*\n\n"
            "📞 *Lagar sampark kara:*\n"
            "• Kisan Call Center: *1800-180-1551* (Free, 24/7)\n"
            "• Pune Krushi Vibhag: 020-26130990\n"
            "• KVK Pune: 020-25695081\n\n"
            "_KrishiMitra — Expert la pathavat ahe_ 🙏")

def _schemes_fallback():
    return ("🏛️ *Mukhya Yojana:*\n\n"
            "1️⃣ *PM-KISAN* — ₹6,000/year\n   👉 pmkisan.gov.in | 155261\n\n"
            "2️⃣ *Pik Vima* — Kandya+Tomato covered\n   👉 Bank madhe apply\n\n"
            "3️⃣ *KCC Loan* — ₹3L at 4%\n   👉 Nazdikchi bank\n\n"
            "4️⃣ *Drip Subsidy* — 55% off\n   👉 Krushi Vibhag\n\n"
            "📞 *1800-180-1551* (Free)")
