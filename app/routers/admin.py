import logging, asyncio, hmac
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
from app.config import APP_SECRET

log = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

def _auth(s):
    # APP_SECRET set नसेल तर admin पूर्ण बंद (default password कधीच नाही)
    if not APP_SECRET:
        raise HTTPException(503, "APP_SECRET not configured")
    if not s or not hmac.compare_digest(s.encode(), APP_SECRET.encode()):
        raise HTTPException(401, "Wrong admin secret")

class ApproveReq(BaseModel):
    phone: str
    name: Optional[str] = None
    crops: Optional[List[str]] = None
    is_free: bool = False
    # टीप: district/city/lat/lon इथून आता set होत नाहीत — farmer स्वतः WhatsApp वर
    # राज्य → जिल्हा → तालुका निवडतो (आधी इथे "Pune" भरल्याने onboarding अडकायचं).
    # जुन्या requests मध्ये ते fields असले तरी ignore होतात.

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
    from app.services.whatsapp import send_broadcast
    from app.services.message_handler import _build_state_select, CONSENT_LINE
    data = {"is_free": req.is_free}
    if req.name: data["name"] = req.name
    if req.crops: data["crops"] = req.crops
    ok = await approve_farmer(req.phone, data)
    if ok:
        await send_broadcast(req.phone,
            "✅ *KrishiMitra मध्ये स्वागत!*\n\n"
            "तुमची नोंदणी मंजूर झाली! 🎉\n\n" + _build_state_select() + "\n\n" + CONSENT_LINE)
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
    from app.services.whatsapp import send_broadcast
    farmers = await get_all_farmers()
    sent = 0
    failed = 0
    for f in farmers:
        try:
            # टीप: आधी send_message चा result न बघताच sent मोजायचो — आता फक्त खरोखर गेलेले मोजतो.
            # (24 तासांत farmer ने message केला नसेल तर Meta free-form text नाकारतो.)
            if await send_broadcast(f["phone"], f"📢 *KrishiMitra:*\n\n{message}"):
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.5)
        except Exception:
            failed += 1
    return {"sent":sent,"failed":failed,"total":len(farmers)}

@router.get("/feedback")
async def feedback(rating: str = "down", limit: int = 50,
                   s: Optional[str] = Header(None, alias="X-Admin-Secret")):
    """शेतकऱ्यांनी दिलेले 👍(up)/👎(down) — खराब उत्तरं तपासून golden dataset मध्ये टाका."""
    _auth(s)
    from app.services.database import get_db
    db = get_db()
    if not db: raise HTTPException(500, "DB error")
    limit = max(1, min(limit, 200))
    r = (db.table("feedback").select("*").eq("rating", rating)
           .order("created_at", desc=True).limit(limit).execute())
    up = db.table("feedback").select("id", count="exact").eq("rating", "up").execute()
    down = db.table("feedback").select("id", count="exact").eq("rating", "down").execute()
    return {"up": up.count or 0, "down": down.count or 0, "items": r.data}
