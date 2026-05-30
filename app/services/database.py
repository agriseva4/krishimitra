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
            "is_blocked": False, "district": "Pune", "city": "Pune",
            "lat": 18.5204, "lon": 73.8567,
            "crops": ["onion", "tomato"], "language": "mr"
        }).execute()
        log.info(f"New farmer: {phone}")
    except Exception as e:
        log.error(f"create_farmer: {e}")

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
    """Last N messages fetch karo — AI la conversation memory milel"""
    try:
        db = get_db()
        if not db: return []
        r = db.table("conversations")\
            .select("user_message,bot_response")\
            .eq("farmer_phone", phone)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        # Reverse karo — oldest first
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
