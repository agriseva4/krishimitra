import logging, asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)
_s = AsyncIOScheduler()

def start_scheduler():
    if _s.running: return
    _s.add_job(morning, CronTrigger(hour=7, minute=0), id="morning", replace_existing=True)
    _s.add_job(evening, CronTrigger(hour=18, minute=0), id="evening", replace_existing=True)
    _s.add_job(weekly, CronTrigger(day_of_week="mon", hour=8, minute=0), id="weekly", replace_existing=True)
    _s.start()
    log.info("✅ Scheduler: 7AM weather | 6PM tip | Monday mandi")

async def morning():
    try:
        from app.services.database import get_all_farmers
        from app.services.weather import get_weather
        from app.services.whatsapp import send_message
        for f in await get_all_farmers():
            try:
                w = await get_weather(f.get("lat"), f.get("lon"), f.get("city","Pune"))
                await send_message(f["phone"], f"🌅 *Suprabhat! — KrishiMitra*\n\n{w}")
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Morning {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Morning batch: {e}")

async def evening():
    try:
        from app.services.database import get_all_farmers
        from app.services.whatsapp import send_message
        tip = _tip(datetime.now().month)
        for f in await get_all_farmers():
            try:
                await send_message(f["phone"], tip)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Evening {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Evening batch: {e}")

async def weekly():
    try:
        from app.services.database import get_all_farmers
        from app.services.mandi import get_mandi_prices
        from app.services.whatsapp import send_message
        mandi = await get_mandi_prices("Pune")
        msg = f"📊 *Saptyahik Mandi Ahval — KrishiMitra*\n\n{mandi}"
        for f in await get_all_farmers():
            try:
                await send_message(f["phone"], msg)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.warning(f"Weekly {f.get('phone')}: {e}")
    except Exception as e:
        log.error(f"Weekly batch: {e}")

def _tip(m):
    tips = {
        1:"❄️ *January:* Kandyala thand pasun vachava. Khate dene thamba.",
        2:"🌸 *February:* Tomato fungicide spray kara. Kandya harvest check kara.",
        3:"☀️ *March:* Una vaadho — paani jaas dya. Kandya store suru kara.",
        4:"🌡️ *April:* Tomato la shade net lava. Paani sakal-sayan dya.",
        5:"💧 *May:* Pre-monsoon tayari. Naali saaf kara. Biyane order kara.",
        6:"🌧️ *June:* Paus suru — Fungicide spray tayar. Drainage check kara.",
        7:"🌾 *July:* Kharip lavnyaas vel. Pausa madhe spray karu naka.",
        8:"🌿 *August:* Tomato la stake kara. Kandya nursery tayar kara.",
        9:"📅 *September:* Rabi tayari. Jamin tapasni. Soil Health Card kadhaa.",
        10:"🧅 *October:* Kandya lavnyaas uttam vel. Biyane tapasaa.",
        11:"🌱 *November:* Kandya + Tomato la khate dya. Havaman cool hote.",
        12:"❄️ *December:* Thand pasun pik vachava. Drip irrigation check kara.",
    }
    return f"{tips.get(m,'🌾 KrishiMitra: Pikachi kaळji ghya!')}\n\n❓ Prashn asel tar pathva!\n_— KrishiMitra_ 🌾"
