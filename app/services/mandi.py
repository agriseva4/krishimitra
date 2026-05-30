import logging, httpx
from datetime import date, timedelta
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from app.config import DATA_GOV_API_KEY

log = logging.getLogger(__name__)
TO = httpx.Timeout(12.0, connect=5.0)

DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
AGMARKNET_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"

# District → Markets mapping
DISTRICT_MARKETS = {
    "pune":       ["Pune", "Pimpri"],
    "nashik":     ["Lasalgaon", "Pimpalgaon", "Ozar", "Rahuri"],
    "solapur":    ["Solapur", "Pandharpur"],
    "ahmednagar": ["Rahuri", "Shrirampur", "Ahmednagar"],
    "mumbai":     ["Vashi"],
    "sangli":     ["Sangli", "Miraj"],
    "satara":     ["Satara", "Karad"],
    "kolhapur":   ["Kolhapur"],
    "jalgaon":    ["Jalgaon", "Bhusawal"],
    "aurangabad": ["Aurangabad", "Lasur"],
    "latur":      ["Latur", "Udgir"],
    "nanded":     ["Nanded", "Mudkhed"],
}

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

    # District nusar markets get karo
    district_lower = district.lower()
    markets = DISTRICT_MARKETS.get(district_lower, [district])

    all_prices = []

    # Pratyek market sathi data fetch karo
    for market in markets:
        for c in crops:
            # Try Data.gov.in first
            if DATA_GOV_API_KEY and DATA_GOV_API_KEY != "PASTE_HERE":
                try:
                    prices = await _fetch_data_gov(c, district, market)
                    all_prices.extend(prices)
                except Exception as e:
                    log.warning(f"Data.gov {market} {c}: {e}")

            # Fallback: Agmarknet
            if not any(p.get("market") == market for p in all_prices):
                try:
                    prices = await _fetch_agmarknet(c, district, today, market)
                    all_prices.extend(prices)
                except Exception as e:
                    log.warning(f"Agmarknet {market} {c}: {e}")

    # Yesterday fallback
    if not all_prices:
        yday = (date.today() - timedelta(days=1)).strftime("%d-%b-%Y")
        for c in crops:
            try:
                prices = await _fetch_agmarknet(c, district, yday)
                all_prices.extend(prices)
            except:
                pass

    # DB history fallback
    if not all_prices:
        from app.services.database import get_mandi_history
        for c in crops:
            hist = await get_mandi_history(c, district, 7)
            if hist:
                all_prices.extend([{
                    "commodity": h["commodity"], "market": h["market"],
                    "min_price": h["min_price"], "max_price": h["max_price"],
                    "modal_price": h["modal_price"], "source": "saved"
                } for h in hist[:3]])

    if all_prices:
        await _store(all_prices, district)
        return _fmt(all_prices, today, district)

    return _fallback(today, district)

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
       retry=retry_if_exception_type(httpx.TimeoutException))
async def _fetch_data_gov(commodity: str, district: str, market: str = None) -> list:
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "limit": "5",
        "filters[State]": "Maharashtra",
        "filters[District]": district,
        "filters[Commodity]": commodity,
    }
    if market:
        params["filters[Market]"] = market
    async with httpx.AsyncClient(timeout=TO) as c:
        r = await c.get(DATA_GOV_URL, params=params)
        if r.status_code == 200:
            records = r.json().get("records", [])
            results = []
            for rec in records[:4]:
                try:
                    results.append({
                        "commodity": rec.get("Commodity", commodity),
                        "market": rec.get("Market", market or district),
                        "min_price": float(rec.get("Min Price", 0) or 0),
                        "max_price": float(rec.get("Max Price", 0) or 0),
                        "modal_price": float(rec.get("Modal Price", 0) or 0),
                        "source": "live"
                    })
                except: continue
            return results
    return []

@retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
       retry=retry_if_exception_type(httpx.TimeoutException))
async def _fetch_agmarknet(commodity: str, district: str, date_str: str, market: str = "All") -> list:
    params = {
        "Tx_Commodity": commodity, "Tx_State": "Maharashtra",
        "Tx_District": district, "Tx_Market": market,
        "DateFrom": date_str, "DateTo": date_str,
        "Fr_Date": date_str, "To_Date": date_str,
        "Tx_Trend": "0", "Tx_CommodityHead": commodity,
        "Tx_StateHead": "Maharashtra", "Tx_DistrictHead": district,
        "Tx_MarketHead": market
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
                        "min_price": float(cols[4].replace(",","") or 0),
                        "max_price": float(cols[5].replace(",","") or 0),
                        "modal_price": float(cols[6].replace(",","") or 0),
                        "source": "live"
                    })
                except: continue
        return results
    except Exception as e:
        log.error(f"Parse: {e}")
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
                f"• ७ दिवसांपूर्वी: ₹{first:.0f}\n• आज: ₹{last:.0f}\n\n"
                f"_Source: KrishiMitra DB_")
    except Exception as e:
        log.error(f"Trend: {e}")
        return "📊 Trend calculate करता आला नाही."

def _fmt(prices: list, date_str: str, district: str) -> str:
    lines = [f"📊 *{district} मंडई भाव — {date_str}*\n"]
    seen = set()
    for p in prices:
        key = f"{p['commodity']}_{p.get('market','')}"
        if key in seen: continue
        seen.add(key)
        emoji = "🧅" if "Onion" in p["commodity"] else "🍅" if "Tomato" in p["commodity"] else "🌾"
        src = "✅ Live" if p.get("source") == "live" else "📦 Saved"
        lines.append(
            f"{emoji} *{p['commodity']}* — {p.get('market', district)}\n"
            f"   किमान: ₹{p.get('min_price',0):.0f} | कमाल: ₹{p.get('max_price',0):.0f} | "
            f"*Modal: ₹{p.get('modal_price',0):.0f}*/क्विंटल {src}\n"
        )
    lines.append("━━━━━━━━━━━━")
    lines.append("_Source: data.gov.in / Agmarknet_")
    return "\n".join(lines)

def _fallback(date_str: str, district: str) -> str:
    markets = DISTRICT_MARKETS.get(district.lower(), [district])
    market_str = ", ".join(markets)
    return (f"📊 *{district} मंडई भाव — {date_str}*\n\n"
            f"⚠️ Live data सध्या उपलब्ध नाही.\n\n"
            f"*{district} जवळच्या मंडया:* {market_str}\n\n"
            f"*इथे तपासा:*\n"
            f"🌐 agmarknet.gov.in\n"
            f"🌐 data.gov.in\n\n"
            f"📞 किसान हेल्पलाइन: 1800-180-1551\n"
            f"_KrishiMitra_ 🌾")
