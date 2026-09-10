import logging, time
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
from app.config import META_VERIFY_TOKEN
from app.services.message_handler import handle
from app.services.whatsapp import send_message
from app.services.database import try_claim_message

log = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# टीप: "double answer" bug चं खरं कारण — Render free-tier झोपलेली असताना (cold-start
# 50+ सेकंद) WhatsApp चा webhook वेळेत उत्तर न मिळाल्याने तोच संदेश परत पाठवतो (retry).
# आधी इथे फक्त in-memory dict वापरून duplicate ओळखलं जायचं — पण तेच cold-start ज्यामुळे
# retry येतो, तेच अनेकदा process restart सुद्धा घडवतं, आणि restart झाला की हा dict
# रिकामा व्हायचा! त्यामुळे नेमकं ज्या वेळी duplicate detection सर्वात जास्त गरजेचं असतं
# (cold-start नंतर), तेव्हाच ते अयशस्वी व्हायचं — district/taluka select सारखे टप्पे
# त्यामुळे 2 वेळा process व्हायचे. आता in-memory (जलद, पहिला अडथळा) + Supabase-based
# (खात्रीचा, process restart मध्येही टिकणारा) असे दोन्ही स्तर एकत्र वापरतो.
_seen_message_ids: dict = {}
_DEDUP_TTL = 600  # 10 मिनिटं — यापेक्षा जुनी entries आपोआप विसरली जातात

def _is_duplicate_in_memory(msg_id: str) -> bool:
    if not msg_id:
        return False
    now = time.time()
    if len(_seen_message_ids) > 2000:
        cutoff = now - _DEDUP_TTL
        for k in list(_seen_message_ids.keys()):
            if _seen_message_ids[k] < cutoff:
                del _seen_message_ids[k]
    if msg_id in _seen_message_ids:
        return True
    _seen_message_ids[msg_id] = now
    return False

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
        msg_id = msg.get("id", "")

        # पायरी 1 — जलद, in-memory check (बहुतांश duplicates लगेच पकडतो, DB call लागत नाही)
        if _is_duplicate_in_memory(msg_id):
            log.info(f"Duplicate webhook skip (memory): {msg_id}")
            return {"status":"ok"}

        # पायरी 2 — खात्रीचा, Supabase-based check (process restart झाला तरी टिकतो —
        # cold-start नंतरचे retries इथे पकडले जातात, जे in-memory check चुकवू शकतो)
        if not await try_claim_message(msg_id):
            log.info(f"Duplicate webhook skip (database): {msg_id}")
            return {"status":"ok"}

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
        if resp:
            await send_message(phone, resp)
            # Farmer ने VOICE ने विचारलं होतं तर उत्तर सुद्धा voice madhe pathaव —
            # tyala vachaता yet nasel tar hे khूप उपयोगी. Best-effort — TTS fail zala
            # tarी text answer aधीच gela aahe, so farmer कधीच रिकाम्या हाताने राहत नाही.
            if mtype in ("audio", "voice"):
                try:
                    from app.services.tts import text_to_speech
                    from app.services.whatsapp import send_audio_message
                    audio_bytes = await text_to_speech(resp)
                    if audio_bytes:
                        await send_audio_message(phone, audio_bytes)
                except Exception as e:
                    log.warning(f"Voice reply skipped {phone}: {e}")
    except Exception as e:
        log.error(f"Process {phone}: {e}")
        try:
            await send_message(phone, "❌ *थोडी अडचण आली.*\nकृपया पुन्हा प्रयत्न करा. 🙏")
        except:
            pass
