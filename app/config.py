import os
from dotenv import load_dotenv

load_dotenv()

# टीप: सुरक्षिततेसाठी secrets चे default काढले — हे Render env मध्ये set करावेच लागतात.
# (आधी "KrishiMitra@2024#Admin" सारखे default code मध्ये होते — repo public असेल तर कुणालाही दिसतात.)
META_VERIFY_TOKEN    = os.getenv("META_VERIFY_TOKEN", "")
META_ACCESS_TOKEN    = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
META_APP_SECRET      = os.getenv("META_APP_SECRET", "")   # Meta App Dashboard → Settings → Basic → App Secret
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY       = os.getenv("TAVILY_API_KEY", "")
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY         = os.getenv("SUPABASE_KEY", "")
OPENWEATHER_API_KEY  = os.getenv("OPENWEATHER_API_KEY", "")
APP_SECRET           = os.getenv("APP_SECRET", "")        # /admin/* साठी (तुमचा स्वतःचा मोठा random password)
DATA_GOV_API_KEY     = os.getenv("DATA_GOV_API_KEY", "")
DEFAULT_LAT          = float(os.getenv("DEFAULT_LAT", "18.5204"))
DEFAULT_LON          = float(os.getenv("DEFAULT_LON", "73.8567"))
DEFAULT_CITY         = os.getenv("DEFAULT_CITY", "Pune")

def validate():
    keys = {
        "META_ACCESS_TOKEN": META_ACCESS_TOKEN,
        "META_PHONE_NUMBER_ID": META_PHONE_NUMBER_ID,
        "META_VERIFY_TOKEN": META_VERIFY_TOKEN,
        "META_APP_SECRET": META_APP_SECRET,
        "APP_SECRET": APP_SECRET,
        "GEMINI_API_KEY": GEMINI_API_KEY,
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
    if not META_APP_SECRET:
        print("⚠️  META_APP_SECRET नाही — webhook signature तपासली जात नाही (fake requests रोखल्या जाणार नाहीत)")
    if not APP_SECRET:
        print("⚠️  APP_SECRET नाही — /admin/* endpoints बंद राहतील")
