import logging, httpx
from app.config import META_ACCESS_TOKEN, META_PHONE_NUMBER_ID

log = logging.getLogger(__name__)
TO = httpx.Timeout(15.0, connect=5.0)

def _url(): return f"https://graph.facebook.com/v19.0/{META_PHONE_NUMBER_ID}/messages"
def _hdr(): return {"Authorization": f"Bearer {META_ACCESS_TOKEN}", "Content-Type": "application/json"}

async def send_message(to: str, text: str) -> bool:
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        log.warning("META keys missing")
        return False
    if len(text) > 4090: text = text[:4087] + "..."
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.post(_url(), json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to, "type": "text",
                "text": {"body": text, "preview_url": False}
            }, headers=_hdr())
            if r.status_code != 200:
                log.error(f"WA [{r.status_code}]: {r.text[:100]}")
                return False
            return True
    except Exception as e:
        log.error(f"send_message: {e}")
        return False

async def get_media_url(media_id: str) -> str:
    if not media_id: return ""
    try:
        async with httpx.AsyncClient(timeout=TO) as c:
            r = await c.get(f"https://graph.facebook.com/v19.0/{media_id}", headers=_hdr())
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
