import logging
from app.services.weather import get_weather
from app.services.mandi import get_mandi_prices, CROP_MAP

log = logging.getLogger(__name__)

async def build_daily_digest(farmer: dict) -> str:
    """आजचं हवामान + शेतकऱ्याच्या स्वतःच्या पिकांचे मंडई भाव (नोंदलेली पिकं असतील तरच)."""
    w = await get_weather(farmer.get("lat"), farmer.get("lon"), farmer.get("city", "Pune"))
    parts = [f"🌅 *आजचं हवामान आणि भाव — KrishiMitra*\n\n{w}"]
    mapped = []
    for c in farmer.get("crops", []) or []:
        commodity = CROP_MAP.get(str(c).lower())
        if commodity and commodity not in mapped:
            mapped.append(commodity)
    if mapped:
        try:
            parts.append(await get_mandi_prices(farmer.get("district", "Pune"), crops=mapped[:3]))
        except Exception as e:
            log.warning(f"digest mandi: {e}")
    parts.append("❓ काही प्रश्न असल्यास विचारा! संदेश थांबवायला *बंद* लिहा.")
    return "\n\n".join(parts)
