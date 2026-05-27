import os
from dotenv import load_dotenv

load_dotenv()

META_VERIFY_TOKEN    = os.getenv("META_VERIFY_TOKEN", "krishimitra2024secret")
META_ACCESS_TOKEN    = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY", "")
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY         = os.getenv("SUPABASE_KEY", "")
OPENWEATHER_API_KEY  = os.getenv("OPENWEATHER_API_KEY", "")
APP_SECRET           = os.getenv("APP_SECRET", "KrishiMitra@2024#Admin")
DATA_GOV_API_KEY     = os.getenv("DATA_GOV_API_KEY", "")
DEFAULT_LAT          = float(os.getenv("DEFAULT_LAT", "18.5204"))
DEFAULT_LON          = float(os.getenv("DEFAULT_LON", "73.8567"))
DEFAULT_CITY         = os.getenv("DEFAULT_CITY", "Pune")

def validate():
    keys = {
        "META_ACCESS_TOKEN": META_ACCESS_TOKEN,
        "META_PHONE_NUMBER_ID": META_PHONE_NUMBER_ID,
        "GROQ_API_KEY": GROQ_API_KEY,
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
    }
    missing = [k for k, v in keys.items() if not v or v == "PASTE_HERE"]
    if missing:
        print(f"⚠️  Missing: {', '.join(missing)} — some features won't work")
    else:
        print("✅ All API keys loaded!")
