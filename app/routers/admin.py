import logging, asyncio
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.config import APP_SECRET

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

def _auth(s):
    if not s or s != APP_SECRET:
        raise HTTPException(401, "Wrong admin secret")

class ApproveReq(BaseModel):
    phone: str
    name: str = "Farmer"
    district: str = "Pune"
    city: str = "Pune"
    crops: List[str] = []
    lat: float = 18.5204
    lon: float = 73.8567
    is_free: bool = False

@router.get("/farmers")
async def list_farmers(s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    _auth(s)
    from app.services.database import get_db
    db = get_db()
    if not db: raise HTTPException(500, "DB error")
    r = db.table("farmers").select("*").order("created_at", desc=True).execute()
    return {"count": len(r.data), "farmers": r.data}

@router.post("/approve")
async def approve(req: ApproveReq, s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    _auth(s)
    from app.services.database import approve_farmer
    from app.services.whatsapp import send_message
    ok = await approve_farmer(req.phone, {
        "name":req.name,"district":req.district,"city":req.city,
        "crops":req.crops,"lat":req.lat,"lon":req.lon,"is_free":req.is_free
    })
    if ok:
        await send_message(req.phone,
            "✅ *KrishiMitra मध्ये स्वागत!*\n\n"
            "तुमची नोंदणी approve झाली! 🎉\n\n"
            "आता कोणताही शेतीविषयक प्रश्न विचारा 🌾\n\n"
            "_— KrishiMitra तुमचा विश्वासनीय शेतकरी मित्र_ 🙏")
    return {"status":"approved" if ok else "failed","phone":req.phone}

@router.post("/block")
async def block(phone: str, s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    _auth(s)
    from app.services.database import get_db
    db = get_db()
    if not db: raise HTTPException(500, "DB error")
    db.table("farmers").update({"is_approved":False,"is_blocked":True}).eq("phone",phone).execute()
    return {"status":"blocked","phone":phone}

@router.get("/stats")
async def stats(s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    _auth(s)
    from app.services.database import get_db
    db = get_db()
    if not db: raise HTTPException(500, "DB error")
    total = db.table("farmers").select("id",count="exact").execute()
    approved = db.table("farmers").select("id",count="exact").eq("is_approved",True).execute()
    convs = db.table("conversations").select("id",count="exact").execute()
    return {"total":total.count or 0,"approved":approved.count or 0,
            "pending":(total.count or 0)-(approved.count or 0),
            "conversations":convs.count or 0}

@router.post("/broadcast")
async def broadcast(message: str, s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    _auth(s)
    from app.services.database import get_all_farmers
    from app.services.whatsapp import send_message
    farmers = await get_all_farmers()
    sent = 0
    for f in farmers:
        try:
            await send_message(f["phone"], f"📢 *KrishiMitra:*\n\n{message}")
            sent += 1
            await asyncio.sleep(0.5)
        except: pass
    return {"sent":sent,"total":len(farmers)}
