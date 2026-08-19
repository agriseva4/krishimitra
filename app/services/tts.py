import logging
import httpx
from app.config import GROQ_API_KEY

log = logging.getLogger(__name__)
GROQ_TTS_URL = "https://api.groq.com/openai/v1/audio/speech"

# टीप: Groq cha playai-tts model प्रामुख्याने English आवाजासाठी optimize आहे.
# Marathi text टाकलं तरी बोलेल, पण उच्चार पूर्ण नैसर्गिक नसतील (काही शब्द इंग्रजी
# accent सारखे वाटू शकतात). जर उत्तम शुद्ध Marathi आवाज हवा असेल तर स्वतंत्र
# Sarvam.ai (भारतीय भाषांसाठी खास बनवलेलं) किंवा ElevenLabs (Indian voices) वापरून बघा
# — तिथे वेगळी API key लागेल (.env मध्ये नवीन variable add करावी लागेल).
_DEFAULT_VOICE = "Fritz-PlayAI"

def _clean_for_speech(text: str) -> str:
    """WhatsApp formatting (*, _, #, emoji) TTS la nीट vaचता येत नाही — काढून टाक"""
    import re
    text = re.sub(r"[*_#~`]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", text)  # emoji काढ
    return text.strip()

async def text_to_speech(text: str, voice: str = _DEFAULT_VOICE) -> bytes:
    """Marathi/English text ला audio (mp3) madhe convert karto. Fail zala tar b'' return."""
    if not GROQ_API_KEY or not text:
        return b""
    try:
        clean_text = _clean_for_speech(text)[:900]  # WhatsApp audio जास्त लांब नको
        if not clean_text:
            return b""
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_TTS_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "playai-tts",
                    "voice": voice,
                    "input": clean_text,
                    "response_format": "mp3",
                }
            )
            if r.status_code == 200:
                return r.content
            log.error(f"TTS [{r.status_code}]: {r.text[:150]}")
            return b""
    except Exception as e:
        log.error(f"text_to_speech: {e}")
        return b""
