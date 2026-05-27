import logging, httpx
from datetime import date, timedelta
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.config import DATA_GOV_API_KEY

log = logging.getLogger(__name__)
TO = httpx.Timeout(12.0, connect=5.0)

DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"

CROP_MAP = {
    "kandya": "Onion", "kanda": "Onion", "कांदा": "Onion", "onion": "Onion",
    "tomato": "Tomato", "tamatar": "Tomato", "टोमॅटो": "Tomato",
    "wheat": "Wheat", "gavhu": "Wheat", "गहू": "Wheat",
    "maize": "Maize", "makka": "Maize", "मका": "Maize",
    "soybean": "Soyabean", "soya": "Soyabean",
    "cotton": "Cotton", "kapus": "Cotton", "कापूस": "Cotton",
    "potato": "Potato", "batata": "Potato", "बटाटा": "Potato",
    "grapes": "Grapes", "draksha": "Grapes", "द्राक्षे": "Grapes",
}

async def get_mandi_prices(district: str = "Pune", crop: str = None) -> str:
    today = date.today().strftime("%d-%b-%Y")
    crops = [CROP_MAP.get(crop.lower(), crop.capitalize())] if crop else ["Onion", "Tomato"]
    all_prices = []

    if DATA_GOV_API_KEY and DATA_GOV_API_KEY != "PASTE_HERE":
        for c in crops:
            try:
                prices = await _fetch_data_gov(c, district)
                all_prices.extend(prices)
            except Exception as e:
                log.warning(f"Data.gov.in failed for {c}: {e}")

    if not all_prices:
        for c in crops:
            try:
                prices = await _fetch_agmarknet(c, district, today)
                all_prices.extend(prices)
            except Exception as e:
                log.warning(f"Agmarknet failed for {c}: {e}")

    if not all_prices:
        yday = (date.today() - timedelta(days=1)).strftime("%d-%b-%Y")
        for c in crops:
            try:
                prices = await _fetch_agmarknet(c, district, yday)
                all_prices.extend(prices)
            except Exception as e:
                log.warning(f"Yesterday fallback failed for {c}: {e}")

    if not all_prices:
        from app.services.database import get_mandi_history
        for c in crops:
            hist = await get_mandi_history(c, district, 7)
            if hist:
                all_prices.extend([{
                    "commodity": h["commodity"], "market": h["market"],
                    "min_price": h["min_price"], "max_price": h["max_price"],
                    "modal_price": h["modal_price"], "source": "stored"
                } for h in hist[:2]])

    if all_prices:
        await _store(all_prices, district)
        return _fmt(all_prices, today, district)

    return _fallback(today, district)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
       retry=retry_if_exception_type(httpx.TimeoutException))
async def _fetch_data_gov(commodity: str, district: str) -> list:
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": "5",
        "filters[State]": "Maharashtra",
        "filters[District]": district,
        "filters[Commodity]": commodity,
    }
    async with httpx.AsyncClient(timeout=TO) as c:
        r = await c.get(DATA_GOV_URL, params=params)
        if r.status_code == 200:
            data = r.json()
            records = data.get("records", [])
            results = []
            for rec in records[:4]:
                try:
                    results.append({
                        "commodity": rec.get("Commodity", commodity),
                        "market": rec.get("Market", district),
                        "min_price": float(rec.get("Min Price", 0) or 0),
                        "max_price": float(rec.get("Max Price", 0) or 0),
                        "modal_price": float(rec.get("Modal Price", 0) or 0),
                        "source": "data.gov.in"
                    })
                except (ValueError, TypeError):
                    continue
            return results
    return []

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
       retry=retry_if_exception_type(httpx.TimeoutException))
async def _fetch_agmarknet(commodity: str, district: str, date_str: str) -> list:
    params = {
        "Tx_Commodity": commodity, "Tx_State": "Maharashtra",
        "Tx_District": district, "Tx_Market": "All",
        "DateFrom": date_str, "DateTo": date_str,
        "Fr_Date": date_str, "To_Date": date_str,
        "Tx_Trend": "0", "Tx_CommodityHead": commodity,
        "Tx_StateHead": "Maharashtra", "Tx_DistrictHead": district,
        "Tx_MarketHead": "All"
    }
    async with httpx.AsyncClient(timeout=TO) as c:
        r = await c.get(AGMARKNET_URL, params=params)
        if r.status_code == 200:
            return _parse(r.text, commodity)
    return []

def _parse(html: str, commodity: str) -> list:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", {"id": "cphBody_GridPriceData"})
        if not table: return []
        results = []
        for row in table.find_all("tr")[1:5]:
            cols = [td.text.strip() for td in row.find_all("td")]
            if len(cols) >= 7:
                try:
                    results.append({
                        "commodity": commodity,
                        "market": cols[2],
                        "min_price": float(cols[4].replace(",", "") or 0),
                        "max_price": float(cols[5].replace(",", "") or 0),
                        "modal_price": float(cols[6].replace(",", "") or 0),
                        "source": "agmarknet"
                    })
                except (ValueError, IndexError):
                    continue
        return results
    except Exception as e:
        log.error(f"Parse error: {e}")
        return []

async def _store(prices: list, district: str):
    try:
        from app.services.database import store_mandi
        records = [{
            "commodity": p["commodity"], "district": district,
            "market": p.get("market", district),
            "min_price": p.get("min_price", 0),
            "max_price": p.get("max_price", 0),
            "modal_price": p.get("modal_price", 0),
            "price_date": date.today().isoformat()
        } for p in prices]
        await store_mandi(records)
    except Exception as e:
        log.warning(f"Store mandi: {e}")

async def get_trend(commodity: str, district: str = "Pune") -> str:
    try:
        from app.services.database import get_mandi_history
        data = await get_mandi_history(commodity, district, 7)
        if len(data) < 2:
            return f"📊 *{commodity}* साठी पुरेसा डेटा नाही.\n७ दिवसांनंतर trend दिसेल!"
        prices = [d["modal_price"] for d in data]
        first, last = prices[0], prices[-1]
        change = last - first
        pct = (change / first * 100) if first > 0 else 0
        arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        word = "वाढला" if change > 0 else "घटला" if change < 0 else "स्थिर"
        return (f"📊 *{commodity} ७-दिवस Trend — {district}*\n\n"
                f"{arrow} भाव *{word}*: ₹{abs(change):.0f}/क्विंटल ({pct:.1f}%)\n"
                f"• ७ दिवसांपूर्वी: ₹{first:.0f}/क्विंटल\n"
                f"• आज: ₹{last:.0f}/क्विंटल\n"
                f"• {len(data)} दिवसांचा डेटा उपलब्ध\n\n"
                f"_Source: KrishiMitra DB_")
    except Exception as e:
        log.error(f"Trend: {e}")
        return "📊 *Trend calculate करता आला नाही.*"

def _fmt(prices: list, date_str: str, district: str) -> str:
    lines = [f"📊 *{district} मंडई भाव — {date_str}*\n"]
    seen = set()
    for p in prices:
        key = f"{p['commodity']}_{p.get('market','')}"
        if key in seen: continue
        seen.add(key)
        emoji = "🧅" if "Onion" in p["commodity"] else "🍅" if "Tomato" in p["commodity"] else "🌾"
        src = "✅ Live" if p.get("source") in ["data.gov.in", "agmarknet"] else "📦 Saved"
        lines.append(
            f"{emoji} *{p['commodity']}* — {p.get('market', district)}\n"
            f"   किमान: ₹{p.get('min_price',0):.0f} | जास्तीत जास्त: ₹{p.get('max_price',0):.0f} | *Modal: ₹{p.get('modal_price',0):.0f}*/क्विंटल {src}\n"
        )
    lines.append("━━━━━━━━━━━━")
    lines.append("_Source: data.gov.in / Agmarknet_")
    lines.append("\n💡 Trend पाहण्यासाठी: \"कांदा trend\" पाठवा")
    return "\n".join(lines)

def _fallback(date_str: str, district: str) -> str:
    return (f"📊 *मंडई भाव — {date_str}*\n\n"
            f"⚠️ {district} चा live data सध्या उपलब्ध नाही.\n\n"
            f"*इथे तपासा:*\n"
            f"🌐 agmarknet.gov.in\n"
            f"🌐 data.gov.in\n"
            f"🏪 puneapmc.org\n\n"
            f"📞 पुणे APMC: 020-24261756\n"
            f"📞 लासलगाव: 02550-251054\n\n"
            f"_KrishiMitra_ 🌾")
