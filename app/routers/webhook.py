import logging
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from app.config import META_VERIFY_TOKEN
from app.services.message_handler import handle
from app.services.whatsapp import send_message

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

@router.get("")
async def verify(request: Request):
    p = dict(request.query_params)
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == META_VERIFY_TOKEN:
        log.info("✅ Webhook verified!")
        return PlainTextResponse(content=p.get("hub.challenge", ""))
    log.warning("❌ Webhook verify failed!")
    return PlainTextResponse(content="Forbidden", status_code=403)

@router.post("")
async def receive(request: Request, bg: BackgroundTasks):
    try:
        body = await request.json()
        msgs = (body.get("entry",[{}])[0]
                    .get("changes",[{}])[0]
                    .get("value",{})
                    .get("messages",[]))
        if not msgs: return {"status":"ok"}
        msg = msgs[0]
        phone = msg.get("from","")
        mtype = msg.get("type","text")
        if phone: bg.add_task(_process, phone, msg, mtype)
        return {"status":"ok"}
    except Exception as e:
        log.error(f"Webhook: {e}")
        return {"status":"ok"}

async def _process(phone, msg, mtype):
    try:
        # 100% Marathi acknowledgement
        ack_map = {
            "image":  "📸 *फोटो मिळाला!*\nपीक रोग तपासतो... थोडा वेळ थांबा 🔬",
            "audio":  "🎤 *व्हॉइस मेसेज मिळाला!*\nसमजून घेतो... थोडा वेळ थांबा ⏳",
            "voice":  "🎤 *व्हॉइस मेसेज मिळाला!*\nसमजून घेतो... थोडा वेळ थांबा ⏳",
            "location": "📍 *तुमचे स्थान मिळाले!*\nहवामान तपासतो... ⏳",
        }
        ack = ack_map.get(mtype, "🌾 *प्रश्न मिळाला!*\nउत्तर तयार करतो... थोडा वेळ थांबा ⏳")
        await send_message(phone, ack)
        resp = await handle(phone, msg, mtype)
        if resp: await send_message(phone, resp)
    except Exception as e:
        log.error(f"Process {phone}: {e}")
        try:
            await send_message(phone, "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏")
        except:
            pass
