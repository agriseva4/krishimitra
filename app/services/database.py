import logging
from typing import Optional
from app.config import SUPABASE_URL, SUPABASE_KEY

log = logging.getLogger(__name__)
_db = None

def get_db():
    global _db
    if _db: return _db
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("❌ Supabase keys missing!")
        return None
    try:
        from supabase import create_client
        _db = create_client(SUPABASE_URL, SUPABASE_KEY)
        log.info("✅ Supabase connected!")
        return _db
    except Exception as e:
        log.error(f"Supabase error: {e}")
        return None

async def get_farmer(phone: str) -> Optional[dict]:
    try:
        db = get_db()
        if not db: return None
        r = db.table("farmers").select("*").eq("phone", phone).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        log.error(f"get_farmer: {e}")
        return None

async def create_farmer(phone: str):
    try:
        db = get_db()
        if not db: return
        if db.table("farmers").select("id").eq("phone", phone).execute().data:
            return
        db.table("farmers").insert({
            "phone": phone, "is_approved": False, "is_free": False,
            "is_blocked": False, "state": "", "district": "", "taluka": "", "city": "",
            "lat": 18.5204, "lon": 73.8567,
            "crops": [], "language": "mr",
            "location_set": False
        }).execute()
        log.info(f"New farmer: {phone}")
    except Exception as e:
        log.error(f"create_farmer: {e}")

async def update_farmer_state(phone: str, state: str):
    """पायरी 1 — राज्य निवडलं (सध्या फक्त Maharashtra)"""
    try:
        db = get_db()
        if not db: return
        db.table("farmers").update({"state": state}).eq("phone", phone).execute()
        log.info(f"State updated: {phone} → {state}")
    except Exception as e:
        log.error(f"update_farmer_state: {e}")

async def update_farmer_district(phone: str, district_key: str, district_name: str):
    """पायरी 2 — जिल्हा निवडला (लगेच नंतर तालुका विचारला जाईल, location_set अजून True होत नाही)"""
    try:
        db = get_db()
        if not db: return
        from app.data.maharashtra_locations import get_district_coords
        lat, lon = get_district_coords(district_key)
        db.table("farmers").update({
            "district": district_name, "city": district_name,
            "lat": lat, "lon": lon,
        }).eq("phone", phone).execute()
        log.info(f"District updated: {phone} → {district_name}")
    except Exception as e:
        log.error(f"update_farmer_district: {e}")

async def update_farmer_taluka(phone: str, taluka: str):
    """पायरी 3 (शेवटची) — तालुका निवडला, आता location_set = True"""
    try:
        db = get_db()
        if not db: return
        db.table("farmers").update({
            "taluka": taluka,
            "location_set": True
        }).eq("phone", phone).execute()
        log.info(f"Taluka updated: {phone} → {taluka}")
    except Exception as e:
        log.error(f"update_farmer_taluka: {e}")

async def update_farmer_location(phone: str, district: str, info: dict):
    """टीप: जुना 1-पायरी location flow (backward-compat साठी ठेवलंय, आता वापरलं जात नाही —
    नवीन 3-पायरी state→district→taluka flow message_handler.py मध्ये आहे)"""
    try:
        db = get_db()
        if not db: return
        db.table("farmers").update({
            "district": district.capitalize(),
            "city": district.capitalize(),
            "lat": info["lat"],
            "lon": info["lon"],
            "location_set": True
        }).eq("phone", phone).execute()
        log.info(f"Location updated: {phone} → {district}")
    except Exception as e:
        log.error(f"update_farmer_location: {e}")

async def update_farmer_crops(phone: str, crops: list):
    """Naveen pikache naव message madhe sapadल्यावर farmer.crops update kar"""
    try:
        db = get_db()
        if not db: return
        # Duplicate kadhun TaK, max 10 crops save kar (table bloat टाळण्यासाठी)
        unique_crops = list(dict.fromkeys(crops))[:10]
        db.table("farmers").update({
            "crops": unique_crops
        }).eq("phone", phone).execute()
        log.info(f"Crops updated: {phone} → {unique_crops}")
    except Exception as e:
        log.error(f"update_farmer_crops: {e}")

async def get_all_farmers() -> list:
    try:
        db = get_db()
        if not db: return []
        r = db.table("farmers").select("*").eq("is_approved", True).eq("is_blocked", False).execute()
        return r.data or []
    except Exception as e:
        log.error(f"get_all_farmers: {e}")
        return []

async def get_last_messages(phone: str, limit: int = 3) -> list:
    try:
        db = get_db()
        if not db: return []
        r = db.table("conversations")\
            .select("user_message,bot_response")\
            .eq("farmer_phone", phone)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return list(reversed(r.data or []))
    except Exception as e:
        log.warning(f"get_last_messages: {e}")
        return []

async def log_conv(phone: str, user: str, bot: str, mtype: str = "text"):
    try:
        db = get_db()
        if not db: return
        db.table("conversations").insert({
            "farmer_phone": phone,
            "message_type": mtype,
            "user_message": (user or "")[:500],
            "bot_response": (bot or "")[:1000]
        }).execute()
    except Exception as e:
        log.warning(f"log_conv: {e}")

async def approve_farmer(phone: str, data: dict) -> bool:
    try:
        db = get_db()
        if not db: return False
        db.table("farmers").update({"is_approved": True, **data}).eq("phone", phone).execute()
        return True
    except Exception as e:
        log.error(f"approve_farmer: {e}")
        return False

async def store_mandi(records: list):
    try:
        db = get_db()
        if not db or not records: return
        db.table("mandi_prices").upsert(records).execute()
    except Exception as e:
        log.warning(f"store_mandi: {e}")

async def get_mandi_history(commodity: str, district: str, days: int = 7) -> list:
    try:
        from datetime import date, timedelta
        db = get_db()
        if not db: return []
        since = (date.today() - timedelta(days=days)).isoformat()
        r = db.table("mandi_prices")\
            .select("*")\
            .eq("commodity", commodity)\
            .eq("district", district)\
            .gte("price_date", since)\
            .order("price_date").execute()
        return r.data or []
    except Exception as e:
        log.warning(f"get_mandi_history: {e}")
        return []

async def try_claim_broadcast(broadcast_type: str) -> bool:
    """आजचा broadcast (morning/daily_mandi/evening) पाठवायचा हक्क "claim" करतो.
    Render वर deploy/restart दरम्यान क्षणभर 2 processes एकत्र चालू राहिल्यास, दोन्ही
    आपापला scheduler घेऊन याच वेळी broadcast पाठवायचा प्रयत्न करतील — त्यामुळे farmer ला
    duplicate messages जायचे. इथे Supabase च्या PRIMARY KEY (broadcast_type, date) मुळे
    फक्त एकच process insert यशस्वी करू शकते — तीच पुढे जाऊन प्रत्यक्ष पाठवते, दुसरी आपोआप थांबते."""
    try:
        from datetime import date
        db = get_db()
        if not db: return True  # DB unavailable असेल तर जुनी पद्धत (पाठव, risk स्वीकार)
        today = date.today().isoformat()
        db.table("broadcast_log").insert({
            "broadcast_type": broadcast_type,
            "broadcast_date": today
        }).execute()
        return True  # insert यशस्वी — या process ने आजचा हक्क जिंकला
    except Exception as e:
        # Unique constraint violation म्हणजे दुसऱ्या process ने आधीच पाठवलंय — थांब
        log.info(f"Broadcast '{broadcast_type}' आधीच claim झालाय आज, skip: {e}")
        return False

async def try_claim_message(message_id: str) -> bool:
    """WhatsApp कडून येणारा प्रत्येक incoming message एकदाच process व्हावा यासाठी.
    टीप: आधी हा check फक्त process च्या memory मध्ये (dict) होता — Render restart/cold-start
    झाला की तो dict रिकामा व्हायचा, आणि नेमकं तेव्हाच (cold-start मुळे उशीर झाल्याने) WhatsApp
    चा retry यायचा — त्यामुळे duplicate ओळखलाच जायचा नाही. आता Supabase (शेअर्ड, कायमस्वरूपी)
    मध्ये ठेवल्यामुळे process कितीही वेळा restart झाला तरी अचूक ओळखलं जातं.
    Returns True तरच पुढे process कर — False असेल तर हा संदेश आधीच हाताळलेला आहे, skip कर."""
    if not message_id:
        return True  # message_id नसेल तर (क्वचित घडतं) जुनी पद्धत — process कर
    try:
        db = get_db()
        if not db: return True  # DB unavailable असेल तर जुनी पद्धत (process कर, risk स्वीकार)
        db.table("processed_messages").insert({"message_id": message_id}).execute()
        return True  # insert यशस्वी — पहिल्यांदाच आलेला संदेश
    except Exception as e:
        # Unique constraint violation म्हणजे हा message_id आधीच process झालाय — duplicate!
        log.info(f"Duplicate message (DB-level) skip: {message_id}")
        return False
