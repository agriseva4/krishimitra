import logging
from app.services.whatsapp import send_message, send_buttons
from app.services.database import get_db, get_last_messages

log = logging.getLogger(__name__)

FB_UP = "fb_up"
FB_DOWN = "fb_down"

async def ask_feedback(phone: str):
    """उत्तरानंतर 👍/👎 बटणं पाठवतो — शेतकऱ्याला फक्त एक टॅप."""
    await send_buttons(
        phone,
        "🙏 हे उत्तर तुम्हाला उपयोगी वाटलं का?",
        [(FB_UP, "👍 उपयोगी"), (FB_DOWN, "👎 उपयोगी नाही")],
    )

async def save_feedback(phone: str, rating: str):
    """शेवटचा प्रश्न-उत्तर (conversations मधून) सोबत जोडून feedback table मध्ये साठवतो."""
    try:
        db = get_db()
        if not db:
            return
        last = await get_last_messages(phone, limit=1)
        q = (last[0].get("user_message") if last else "") or ""
        a = (last[0].get("bot_response") if last else "") or ""
        db.table("feedback").insert({
            "farmer_phone": phone, "rating": rating,
            "user_message": q[:500], "bot_response": a[:1000],
        }).execute()
    except Exception as e:
        log.warning(f"save_feedback: {e}")

async def handle_feedback_reply(phone: str, msg: dict):
    """शेतकऱ्याने 👍/👎 दाबल्यावर — साठवून मराठीत छोटं उत्तर."""
    reply = (msg.get("interactive") or {}).get("button_reply") or {}
    bid = reply.get("id", "")
    if bid not in (FB_UP, FB_DOWN):
        return
    await save_feedback(phone, "up" if bid == FB_UP else "down")
    if bid == FB_UP:
        await send_message(phone, "🙏 धन्यवाद! आणखी काही विचारायचं असेल तर पाठवा 🌾")
    else:
        await send_message(
            phone,
            "माफ करा 🙏 तुम्हाला हवं तसं उत्तर मिळालं नाही.\n\n"
            "कृपया *पीक आणि समस्या* थोडी सविस्तर लिहून पुन्हा विचारा (शक्य असेल तर फोटोही पाठवा 📸), "
            "किंवा 📞 1800-180-1551 (मोफत) वर संपर्क करा.")
