import asyncio, logging, os, httpx
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import META_ACCESS_TOKEN, META_PHONE_NUMBER_ID

log = logging.getLogger(__name__)
TO = httpx.Timeout(15.0, connect=5.0)

# टीप: Meta जुन्या API versions कालांतराने बंद करतो. version Render env मध्ये ठेवली — Meta App Dashboard मध्ये
# तुमच्या app ला दाखवलेली version इथे द्या (WA_GRAPH_VERSION=vXX.0); code बदलावा लागत नाही.
GRAPH_VER = os.getenv("WA_GRAPH_VERSION", "v19.0")

def mask_phone(p: str) -> str:
    """logs मध्ये पूर्ण फोन नंबर नको (गोपनीयता): 919876543210 → 91******3210"""
    p = str(p or "")
    return (p[:2] + "*" * max(0, len(p) - 6) + p[-4:]) if len(p) > 6 else "***"

def _url(): return f"https://graph.facebook.com/{GRAPH_VER}/{META_PHONE_NUMBER_ID}/messages"
def _hdr(): return {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}

REENGAGE_CODE = 131047   # Meta: "Re-engagement message" — farmer ने गेल्या 24 तासांत message केला नाही
WA_NUDGE_TEMPLATE = os.getenv("WA_NUDGE_TEMPLATE", "")   # Meta मध्ये approve केलेल्या template चं नाव
WA_NUDGE_LANG = os.getenv("WA_NUDGE_LANG", "mr")
_IST = ZoneInfo("Asia/Kolkata")
_nudged = {}   # phone -> शेवटची nudge तारीख (IST)

def _today():
    return datetime.now(_IST).date().isoformat()

async def send_message_ex(to: str, text: str):
    """(ok, error_code) परत करतो — error_code Meta चा (उदा. 131047) किंवा None.
    तात्पुरत्या अडचणीत (Meta 429/5xx, connect error) एकदा पुन्हा प्रयत्न करतो. ReadTimeout वर नाही —
    कारण तेव्हा संदेश कदाचित गेलेला असतो आणि पुन्हा पाठवल्यास शेतकऱ्याला दोनदा दिसेल."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        log.warning("META keys missing")
        return False, None
    if len(text) > 4090: text = text[:4087] + "..."
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to, "type": "text",
        "text": {"body": text, "preview_url": False}
    }
    for attempt in (1, 2):
        try:
            async with httpx.AsyncClient(timeout=TO) as c:
                r = await c.post(_url(), json=payload, headers=_hdr())
            if r.status_code == 200:
                return True, None
            code = None
            try:
                code = (r.json().get("error") or {}).get("code")
            except Exception:
                pass
            if attempt == 1 and (r.status_code == 429 or r.status_code >= 500):
                await asyncio.sleep(1.5)
                continue
            log.error(f"WA [{r.status_code}] code={code}: {r.text[:100]}")
            return False, code
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if attempt == 1:
                await asyncio.sleep(1.5)
                continue
            log.error(f"send_message connect: {e}")
            return False, None
        except Exception as e:
            log.error(f"send_message: {e}")
            return False, None
    return False, None

async def send_message(to: str, text: str) -> bool:
    ok, _code = await send_message_ex(to, text)
    return ok

async def send_template(to: str, name: str, lang: str = "mr", body_params: list = None) -> bool:
    """Meta ने approve केलेला template पाठवतो (24-तास window बाहेरही चालतो)."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID or not name:
        return False
    try:
        tpl = {"name": name, "language": {"code": lang}}
        if body_params:
            tpl["components"] = [{"type": "body",
                                  "parameters": [{"type": "text", "text": str(x)} for x in body_params]}]
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.post(_url(), json={"messaging_product": "whatsapp", "to": to,
                                           "type": "template", "template": tpl}, headers=_hdr())
            if r.status_code != 200:
                log.error(f"WA template [{r.status_code}]: {r.text[:140]}")
                return False
            return True
    except Exception as e:
        log.error(f"send_template: {e}")
        return False

async def send_broadcast(to: str, text: str) -> bool:
    """रोजचे/प्रोॲक्टिव्ह संदेश: आधी साधा text; farmer 24 तासांच्या window बाहेर असेल (131047)
    तर, आणि WA_NUDGE_TEMPLATE set असेल तर, दिवसातून एकदा छोटा template ("हो म्हणा") पाठवतो.
    शेतकऱ्याने 'हो' म्हटलं की window उघडते आणि message_handler आजचं हवामान+भाव पाठवतो."""
    ok, code = await send_message_ex(to, text)
    if ok:
        return True
    if code == REENGAGE_CODE and WA_NUDGE_TEMPLATE and _nudged.get(to) != _today():
        if await send_template(to, WA_NUDGE_TEMPLATE, WA_NUDGE_LANG):
            _nudged[to] = _today()
            return True
    return False

def was_nudged_recently(phone: str) -> bool:
    d = _nudged.get(phone)
    if not d:
        return False
    today = datetime.now(_IST).date()
    try:
        return (today - datetime.fromisoformat(d).date()).days <= 1
    except Exception:
        return False

def clear_nudge(phone: str):
    _nudged.pop(phone, None)

async def get_media_url(media_id: str) -> str:
    if not media_id: return ""
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.get(f"https://graph.facebook.com/{GRAPH_VER}/{media_id}", headers=_hdr())
            if r.status_code == 200: return r.json().get("url", "")
    except Exception as e:
        log.error(f"get_media_url: {e}")
    return ""

async def download_media(url: str) -> bytes:
    if not url: return b""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
            r = await c.get(url, headers=_hdr())
            if r.status_code == 200: return r.content
    except Exception as e:
        log.error(f"download_media: {e}")
    return b""

async def upload_media(file_bytes: bytes, mime_type: str = "audio/mpeg") -> str:
    """Audio/image bytes WhatsApp cha media server var upload kar, media_id return karto"""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID or not file_bytes:
        return ""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
            files = {"file": ("voice_reply.mp3", file_bytes, mime_type)}
            data = {"messaging_product": "whatsapp", "type": mime_type}
            r = await c.post(
                f"https://graph.facebook.com/{GRAPH_VER}/{META_PHONE_NUMBER_ID}/media",
                headers={"Authorization": f"Bearer {META_ACCESS_TOKEN}"},
                files=files, data=data
            )
            if r.status_code == 200:
                return r.json().get("id", "")
            log.error(f"upload_media [{r.status_code}]: {r.text[:150]}")
    except Exception as e:
        log.error(f"upload_media: {e}")
    return ""

async def send_audio_message(to: str, audio_bytes: bytes) -> bool:
    """TTS ne banवलेला audio farmer la WhatsApp voice message म्हणून pathav"""
    if not audio_bytes:
        return False
    media_id = await upload_media(audio_bytes, "audio/mpeg")
    if not media_id:
        return False
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.post(_url(), json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to, "type": "audio",
                "audio": {"id": media_id}
            }, headers=_hdr())
            if r.status_code != 200:
                log.error(f"WA audio [{r.status_code}]: {r.text[:150]}")
                return False
            return True
    except Exception as e:
        log.error(f"send_audio_message: {e}")
        return False

async def send_buttons(to: str, body: str, buttons: list) -> bool:
    """WhatsApp 'reply buttons' (जास्तीत जास्त 3). buttons = [(id, title), ...] — title 20 अक्षरांपर्यंत.
    टीप: हा template नाही — farmer ने शेवटचा message 24 तासांच्या आत पाठवला असेल तेव्हाच चालतो
    (आपण उत्तरानंतरच पाठवतो, त्यामुळे ठीक)."""
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID or not buttons:
        return False
    try:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to, "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body[:1024]},
                "action": {"buttons": [
                    {"type": "reply", "reply": {"id": bid, "title": title[:20]}}
                    for bid, title in buttons[:3]
                ]},
            },
        }
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.post(_url(), json=payload, headers=_hdr())
            if r.status_code != 200:
                log.error(f"WA buttons [{r.status_code}]: {r.text[:120]}")
                return False
            return True
    except Exception as e:
        log.error(f"send_buttons: {e}")
        return False
