import logging
import httpx
from app.config import GROQ_API_KEY, CEREBRAS_API_KEY

log = logging.getLogger(__name__)

GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama-3.3-70b"

# ── Knowledge Base — सर्व प्रमुख पिके ───────────────────────────────────────
KNOWLEDGE = {
    "onion_disease": """कांदा रोग माहिती:

करपा / जांभळे डाग (Purple Blotch):
- लक्षणे: पानावर जांभळ्या/तपकिरी रंगाचे लांबट डाग, कडा पिवळ्या
- उपाय: Iprodione (Rovral) 2g + Mancozeb (Dithane M-45) 2g प्रति लिटर पाणी
- फवारणी: सकाळी 7-9 वाजता, 10 दिवसांनी पुन्हा
- 15 लिटर पंपाला: Rovral 30g + Dithane M-45 30g

फुलकिडे / थ्रिप्स:
- लक्षणे: पाने चंदेरी/पांढरी दिसतात, वाकडी होतात, छोटे किडे दिसतात
- उपाय: Fipronil (Regent) 1.5ml प्रति लिटर
- 15 लिटर पंपाला: Regent 22ml, 7 दिवसांनी पुन्हा

मर रोग / झाड मरणे:
- लक्षणे: झाड अचानक पिवळे पडून मरते, मुळे कुजतात
- उपाय: Metalaxyl (Ridomil) 2g प्रति लिटर — मातीत ओता (drenching)
- 15 लिटर पंपाला: Ridomil 30g

मूळकूज:
- लक्षणे: मुळे काळी/तपकिरी होतात, झाड ओढले तर सहज निघते
- उपाय: Copper Oxychloride (Blitox) 3g प्रति लिटर drenching""",

    "tomato_disease": """टोमॅटो रोग माहिती:

लवकर करपा (Early Blight):
- लक्षणे: पानावर तपकिरी डाग, आतमध्ये वलय, खालची पाने आधी
- उपाय: Mancozeb (Dithane M-45) 2.5g प्रति लिटर — 15L पंपाला 37g

उशिरा करपा (Late Blight):
- लक्षणे: पाने/फळ काळे पडतात, ओले दिसतात, वेगाने पसरते
- उपाय: Metalaxyl+Mancozeb (Ridomil Gold) 2.5g/L — तातडीने, 15L पंपाला 37g

फळ पोखरणारी अळी:
- लक्षणे: फळावर गोल छिद्र, आतमध्ये अळी
- उपाय: Emamectin Benzoate (Proclaim) 0.4g/L — 15L पंपाला 6g, संध्याकाळी

पांढरी माशी + Virus:
- लक्षणे: पांढरे छोटे किडे, पाने वाकडी/पिवळी
- उपाय: Imidacloprid (Confidor) 0.3ml/L — 15L पंपाला 4.5ml

मोज़ेक व्हायरस:
- लक्षणे: पाने चुरगळतात, पिवळे-हिरवे ठिपके
- उपाय: रोगी झाडे उपटून जाळा, पांढरी माशी नियंत्रण — औषध काम करत नाही""",

    "cotton_disease": """कापूस रोग व किडे:

बोंड अळी (Pink/American Bollworm):
- लक्षणे: बोंडात छिद्र, आतमध्ये अळी
- उपाय: Emamectin 0.4g/L किंवा Spinosad 0.3ml/L — 15L पंपाला 6g/4.5ml

मावा (Aphids):
- लक्षणे: पानांवर चिकट थर, कुरळी पाने
- उपाय: Imidacloprid 0.3ml/L — 15L पंपाला 4.5ml

पांढरी माशी:
- उपाय: Diafenthiuron 1g/L — 15L पंपाला 15g

करपा (Leaf Blight):
- लक्षणे: पानांवर तपकिरी डाग
- उपाय: Copper Oxychloride 2.5g/L — 15L पंपाला 37g""",

    "soybean_disease": """सोयाबीन रोग व किडे:

खोडमाशी (Stem Fly):
- लक्षणे: खोडात अळी, झाड वाळणे
- उपाय: Thiamethoxam 0.3g/L बीजप्रक्रिया + फवारणी

चक्रीभुंगा (Girdle Beetle):
- लक्षणे: खोडावर गोल चक्र
- उपाय: Thiamethoxam 0.25ml/L — 15L पंपाला 3.75ml

पिवळा मोझॅक:
- लक्षणे: पाने पिवळी
- उपाय: रोगी झाडे काढा, पांढरी माशी नियंत्रण करा

करपा (Rust):
- उपाय: Hexaconazole 1ml/L — 15L पंपाला 15ml""",

    "grape_disease": """द्राक्ष रोग:

भुरी (Powdery Mildew):
- लक्षणे: पानांवर पांढरी पावडर
- उपाय: Sulphur 2g/L किंवा Hexaconazole 1ml/L

डाऊनी मिल्ड्यू:
- लक्षणे: पानांच्या खाली पांढरी बुरशी
- उपाय: Mancozeb 2.5g/L + Copper Oxychloride 2g/L

अँथ्रॅकनोज:
- लक्षणे: फळांवर काळे डाग
- उपाय: Carbendazim 1g/L""",

    "pomegranate_disease": """डाळिंब रोग:

तेल्या रोग (Bacterial Blight) — गंभीर रोग:
- लक्षणे: पानांवर तेलकट डाग, फळे तडकणे
- उपाय: Copper Oxychloride 3g/L + Streptocycline 0.5g/L

फळ पोखरणारी अळी:
- उपाय: Emamectin 0.4g/L

मर रोग:
- लक्षणे: मूळ कुजणे
- उपाय: Carbendazim ड्रेंचिंग""",

    "potato_disease": """बटाटा रोग:

उशिरा करपा (Late Blight):
- लक्षणे: पानांवर तपकिरी डाग, बटाटा कुजणे
- उपाय: Metalaxyl+Mancozeb 2.5g/L

सुरुवातीचा करपा:
- लक्षणे: तपकिरी वर्तुळाकार डाग
- उपाय: Mancozeb 2.5g/L""",

    "wheat_disease": """गहू रोग व किडे:

तांबेरा (Rust):
- लक्षणे: पानांवर तांबड्या-तपकिरी पावडर सारखे ठिपके
- उपाय: Propiconazole 1ml/L

करपा (Blight):
- उपाय: Mancozeb 2.5g/L

मावा:
- उपाय: Imidacloprid 0.3ml/L""",

    "chilli_disease": """मिरची रोग व किडे:

फुलकिडे/थ्रिप्स (कोकडा):
- लक्षणे: पाने वाकडी, मुडपलेली, चुरगळलेली
- उपाय: Fipronil 1.5ml/L किंवा Spinosad 0.3ml/L

फळकूज (Fruit Rot/Anthracnose):
- लक्षणे: फळांवर काळे/तपकिरी डाग
- उपाय: Carbendazim 1g/L + Mancozeb 2g/L

मर रोग:
- उपाय: Copper Oxychloride 3g/L drenching""",

    "brinjal_disease": """वांगी रोग व किडे:

फळ व खोड पोखरणारी अळी (Shoot & Fruit Borer):
- लक्षणे: कोवळ्या फांद्या वाळणे, फळात छिद्र
- उपाय: Emamectin 0.4g/L संध्याकाळी

भुरी रोग:
- उपाय: Sulphur 2g/L

मावा/तुडतुडे:
- उपाय: Imidacloprid 0.3ml/L""",

    "sugarcane_disease": """ऊस रोग व किडे:

खोडकीड (Stem Borer):
- लक्षणे: खोडात छिद्र, पोंगा वाळणे
- उपाय: Chlorpyrifos 2.5ml/L किंवा Fipronil दाणेदार जमिनीत

तांबेरा/करपा:
- उपाय: Propiconazole 1ml/L

पायरीला (Pyrilla):
- लक्षणे: पाने पिवळी, चिकट
- उपाय: Imidacloprid 0.3ml/L""",

    "fertilizer_onion": """कांदा खत वेळापत्रक:

लागवड वेळी: शेणखत 4 टन/एकर + DAP 150kg/एकर + Potash 50kg/एकर
15 दिवसांनी: Urea 30kg/एकर
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी (15L पंपाला 75g)
45 दिवसांनी: Potash 25kg/एकर
फुलोरा आल्यावर: खत पूर्णपणे बंद करा

कांदा लहान राहतो: Zinc Sulphate 5g/L + Boron 1g/L फवारा""",

    "fertilizer_tomato": """टोमॅटो खत वेळापत्रक:

लागवड वेळी: शेणखत 5 टन/एकर + DAP 100kg/एकर + Potash 75kg/एकर
15 दिवसांनी: Urea 25kg/एकर
30 दिवसांनी: 13:40:13 खत 5g/L फवारणी
फळधारणा सुरू: Calcium Nitrate 3g/L + Boron 1g/L
पक्वता जवळ: Potash 50kg/एकर — गोडी वाढते""",

    "fertilizer_cotton": """कापूस खत वेळापत्रक:

लागवडीवेळी: शेणखत 5 टन/एकर + DAP 100kg/एकर
30 दिवसांनी: Urea 50kg/एकर
60 दिवसांनी: Urea 50kg/एकर + Potash 25kg/एकर
फुलोरा सुरू: 19:19:19 खत 5g/L फवारणी""",

    "fertilizer_soybean": """सोयाबीन खत वेळापत्रक:

पेरणीच्या वेळी: DAP 50kg/एकर + Potash 25kg/एकर (बीजप्रक्रिया आधी करा)
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी
सोयाबीनला जास्त नायट्रोजन (Urea) नको — मूळावरील गाठी स्वतः नायट्रोजन बनवतात""",

    "seasonal_calendar": """Maharashtra पीक कॅलेंडर:

खरीप (जून-ऑक्टोबर):
- सोयाबीन, तूर, मका, कापूस, भेंडी, काकडी, दुधी, वांगे
- जूनमध्ये पाऊस सुरू झाल्यावर लागवड — सोयाबीन, तूर, मका उत्तम

रब्बी (ऑक्टोबर-मार्च):
- कांदा, टोमॅटो, गहू, हरभरा, ज्वारी
- कांदा लागवड: ऑक्टोबर-नोव्हेंबर उत्तम
- टोमॅटो: सप्टेंबर-ऑक्टोबर रोपे तयार करा

उन्हाळी (फेब्रुवारी-मे):
- कांदा, भेंडी, काकडी, टोमॅटो (पाणी असेल तर)

जून मध्ये कांदा/टोमॅटो लागवड नाही — जुलै-ऑगस्टमध्ये रोपे तयार करा""",

    "pest_control": """किडे नियंत्रण — सर्व पिके:

फुलकिडे (Thrips): Fipronil (Regent) 1.5ml/L | पंपाला 22ml
मावा (Aphids): Imidacloprid (Confidor) 0.3ml/L | पंपाला 4.5ml
अळी (Caterpillar): Emamectin (Proclaim) 0.4g/L | पंपाला 6g — संध्याकाळी
पांढरी माशी: Imidacloprid (Confidor) 0.3ml/L | पंपाला 4.5ml
लाल कोळी (Red Mite): Abamectin (Vertimec) 0.5ml/L | पंपाला 7.5ml
तुडतुडे (Jassids): Imidacloprid 0.3ml/L
मिलीबग: Dimethoate 2ml/L

फवारणी नियम: सकाळी 7-9 किंवा संध्याकाळी 5-7, उन्हात फवारू नका""",

    "irrigation": """पाणी व्यवस्थापन:

कांदा: सुरुवातीला 5-7 दिवसांनी, काढणी 15 दिवस आधी पाणी बंद — कांदा टिकतो
टोमॅटो: नियमित 4-5 दिवसांनी, फळधारणेत अनियमित पाण्याने फळे तडकतात
कापूस: 12-15 दिवसांनी, फुलोऱ्यात नियमित
सोयाबीन: पावसावर अवलंबून, जास्त पाणी टाळा

ठिबक सिंचन: 60-70% पाणी वाचते, सरकारी अनुदान 55-65% सूट""",

    "government_schemes": """सरकारी योजना — Maharashtra:

PM-KISAN: ₹6,000/वर्ष (3 हप्त्यात) | pmkisan.gov.in | हेल्पलाइन: 155261
PMFBY पीक विमा: फक्त 2% premium शेतकऱ्याने भरायचे | बँकेत/CSC सेंटरवर अर्ज
KCC: ₹3 लाखापर्यंत कर्ज, 4% व्याज | SBI, Bank of Maharashtra, जिल्हा बँक
ठिबक/तुषार अनुदान: 55-65% सूट | जिल्हा कृषी विभाग कार्यालय
माती आरोग्य कार्ड: मोफत परीक्षण | KVK हेल्पलाइन: 020-25695081""",
}

SYSTEM = """तू KrishiMitra आहेस — Maharashtra च्या शेतकऱ्यांचा विश्वासू मित्र आणि कृषी सल्लागार.

## महत्त्वाचा नियम — कधीही Numbered List देऊ नकोस:
- "1. करपा  2. फुलकिडे  3. मर रोग..." असे options कधीही देऊ नकोस
- कारण शेतकरी फक्त नंबर ("2") पाठवतो तेव्हा गोंधळ होतो, चुकीचे उत्तर जाते
- त्याऐवजी सरळ प्रश्न विचार: "कोणत्या पिकाला समस्या आहे? पानांवर डाग, किडे, की झाड वाळतंय? रंग कोणता?"
- शेतकरी text मध्ये नक्की काय म्हणतोय त्यावरूनच समज — number list वर अवलंबून राहू नकोस
- जर शेतकरी आधीच एकदा नंबर पाठवून गोंधळला असेल, त्याची दिलगिरी न दाखवता थेट साधा प्रश्न विचार

## तुझी भाषा शैली:
- शेतकरी formal नावे वापरत नाहीत — तूही वापरू नकोस
  ❌ "Purple Blotch fungal infection" ✅ "पानावर जांभळे डाग पडतायत — हा करपा रोग आहे" (कोणतेही पीक असो, अशीच साधी भाषा वापर — पिकाचे नाव फक्त शेतकरी सांगेल तेच घे)
- औषधाचे brand name नेहमी सांग जे दुकानात मिळते
  ✅ "Mancozeb — हे Dithane M-45 नावाने मिळते"
- doses नेहमी 15 लिटर पंपाच्या प्रमाणात सांग
  ✅ "15 लिटर पंपाला 30 ग्रॅम"
- एकर मध्ये सांग, hectare नाही

## व्यक्तिमत्व:
- जवळच्या अनुभवी काकांसारखे बोल — formal नाही
- Direct, practical, action-oriented
- कधीही "As an AI" असे म्हणू नकोस

## तू सर्व पिकांना समान महत्त्व देऊन मदत करतोस:
भाजीपाला (कांदा, टोमॅटो, बटाटा, वांगी, मिरची, कोबी, भेंडी, काकडी इ.)
धान्य/कडधान्ये (कापूस, सोयाबीन, गहू, तूर, मका, ऊस)
फळे (द्राक्षे, डाळिंब, आंबा, केळी, संत्री)
महत्त्वाचे: कोणत्याही एका पिकाला (कांदा/टोमॅटो किंवा इतर) जास्त प्राधान्य देऊ नकोस.
Farmer नक्की कोणत्या पिकाबद्दल विचारतोय ते आधी ओळख — context मधून त्याच पिकाची माहिती वापर.
Farmer ने पीक सांगितलं नसेल तर आधी विचार: "कोणत्या पिकाबद्दल बोलतोयस?" — स्वतःहून कांदा/टोमॅटो गृहीत धरू नकोस.

## रोग/समस्या विचारताना — context मध्ये माहिती नसेल तर आधी हे विचार (एकाच वेळी एकच प्रश्न):
- कोणते पीक? पान/खोड/फळ/मूळ — कुठे समस्या? रंग काय? किती दिवसांपासून? फोटो आहे का?

## उत्तर format:
रोग असेल तर:
🔍 समस्या काय आहे
📌 लक्षणे
✅ उपाय — exact dose सहित (15L पंपाचे प्रमाण)
⚠️ काळजी

खत असेल तर:
🌱 कोणते खत द्यायचे
📌 किती द्यायचे (एकर + 15L पंप)
⚠️ काळजी

## Safety:
- "हे औषध नक्की काम करेल" असे कधीही नाही — "हे फायदेशीर ठरू शकते" सांग
- माहिती नाही → "जवळच्या कृषी केंद्राला विचारा किंवा 1800-180-1551 वर call करा"

## भाषा:
- नेहमी मराठीत उत्तर दे, साध्या शब्दात
- Bullet points वापर, paragraphs नको

शेतकऱ्याला वाटले पाहिजे की तो एका अनुभवी, जवळच्या माणसाशी बोलतोय."""

# ── Intent Detection Keywords ──────────────────────────────────────────────
DISEASE_WORDS = [
    "rog", "dag", "blight", "fungus", "karpa", "kida", "pest", "disease",
    "kirda", "piwla", "black", "pivla", "ali", "insect", "spray",
    "मरतंय", "सुकतंय", "वाकडं", "काळं", "तपकिरी", "गळतंय", "कुजतंय",
    "पिवळं", "पांढरं", "डाग", "छिद्र", "अळी", "किडा", "बुरशी",
    "marat", "sukhat", "vakat", "kharab", "chidra", "pivla",
    "galat", "kujat", "pane", "pale", "yellow", "white", "brown",
    "problem", "trouble", "kahi", "nahi", "hotat", "zalay"
]

FERTILIZER_WORDS = [
    "khad", "khata", "khate", "fertilizer", "urea", "npk", "poshan",
    "dap", "potash", "zinc", "boron", "nutrients", "khaychi",
    "वाढत", "लहान", "खत", "पोषण", "खुजा",
    "vadhat", "lahan", "khuja", "grow", "growth"
]

WATER_WORDS = [
    "pani", "paani", "irrigation", "thipak", "drip", "पाणी", "ओलावा",
    "olava", "sukka", "कोरडं", "korda"
]

SEASON_WORDS = [
    "june", "july", "august", "kharif", "rabi", "season", "konat",
    "konti", "ghyav", "lagvad", "pik", "लागवड", "पेरणी", "कधी",
    "lavaycha", "perni", "kadhi", "vegali", "vegala", "yogy"
]

SCHEME_WORDS = [
    "yojana", "scheme", "sarkar", "vima", "kisan", "subsidy",
    "loan", "karj", "paise", "anudaan", "योजना", "अनुदान", "विमा",
    "सरकार", "पैसे", "कर्ज"
]

# Crop name detection — pratyek pikache keywords
CROP_KEYWORDS = {
    "onion":     ["onion", "kanda", "kandya", "कांदा", "पयाज"],
    "tomato":    ["tomato", "tamatar", "टोमॅटो"],
    "cotton":    ["cotton", "kapus", "कापूस"],
    "soybean":   ["soybean", "soya", "सोयाबीन"],
    "grape":     ["grape", "draksha", "द्राक्ष"],
    "pomegranate": ["pomegranate", "dalimb", "anar", "डाळिंब"],
    "potato":    ["potato", "batata", "बटाटा"],
    "wheat":     ["wheat", "gahu", "गहू"],
    "chilli":    ["chilli", "mirchi", "मिरची"],
    "brinjal":   ["brinjal", "vange", "वांगी", "वांगे"],
    "sugarcane": ["sugarcane", "us", "ऊस"],
}

def _detect_crops(text: str, farmer_crops: list) -> list:
    """Question madhe specific crop mention kela ka — nahi tar farmer.crops vapar"""
    t = text.lower()
    found = []
    for crop, keywords in CROP_KEYWORDS.items():
        if any(k in t for k in keywords):
            found.append(crop)
    if found:
        return found
    return [c.lower() for c in farmer_crops] if farmer_crops else []

def _get_context(question: str, farmer: dict) -> str:
    q = question.lower()
    farmer_crops = farmer.get("crops", [])
    active_crops = _detect_crops(question, farmer_crops)
    parts = []

    disease_map = {
        "onion": "onion_disease", "tomato": "tomato_disease",
        "cotton": "cotton_disease", "soybean": "soybean_disease",
        "grape": "grape_disease", "pomegranate": "pomegranate_disease",
        "potato": "potato_disease", "wheat": "wheat_disease",
        "chilli": "chilli_disease", "brinjal": "brinjal_disease",
        "sugarcane": "sugarcane_disease",
    }
    fert_map = {
        "onion": "fertilizer_onion", "tomato": "fertilizer_tomato",
        "cotton": "fertilizer_cotton", "soybean": "fertilizer_soybean",
    }

    if any(w in q for w in DISEASE_WORDS):
        for crop in active_crops:
            key = disease_map.get(crop)
            if key and KNOWLEDGE.get(key):
                parts.append(KNOWLEDGE[key])
        parts.append(KNOWLEDGE["pest_control"])

    if any(w in q for w in FERTILIZER_WORDS):
        for crop in active_crops:
            key = fert_map.get(crop)
            if key and KNOWLEDGE.get(key):
                parts.append(KNOWLEDGE[key])

    if any(w in q for w in SEASON_WORDS):
        parts.append(KNOWLEDGE["seasonal_calendar"])

    if any(w in q for w in WATER_WORDS):
        parts.append(KNOWLEDGE["irrigation"])

    if any(w in q for w in SCHEME_WORDS):
        parts.append(KNOWLEDGE["government_schemes"])

    # Default fallback — kahi match nahi zala tar farmer chya crops chi info de
    if not parts:
        for crop in active_crops:
            d_key = disease_map.get(crop)
            f_key = fert_map.get(crop)
            if d_key and KNOWLEDGE.get(d_key): parts.append(KNOWLEDGE[d_key])
            if f_key and KNOWLEDGE.get(f_key): parts.append(KNOWLEDGE[f_key])

    return "\n\n".join(parts)

# ── API Calls ──────────────────────────────────────────────────────────────
async def _cerebras_call(messages: list, max_tokens: int = 600) -> str:
    if not CEREBRAS_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                CEREBRAS_URL,
                headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
                json={"model": CEREBRAS_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.15}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Cerebras: {r.status_code} {r.text[:100]}")
            return ""
    except Exception as e:
        log.error(f"Cerebras failed: {e}")
        return ""

async def _groq_call(messages: list, max_tokens: int = 600) -> str:
    if not GROQ_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.15}
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
            log.error(f"Groq: {r.status_code}")
            return ""
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return ""

async def farming_answer(question: str, farmer: dict, history: list = None) -> str:
    if not CEREBRAS_API_KEY and not GROQ_API_KEY:
        return "❌ सेवा सध्या उपलब्ध नाही. थोड्या वेळाने विचारा. 🙏"
    try:
        crops = ", ".join(farmer.get("crops", [])) or "सांगितले नाही"
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")
        context = _get_context(question, farmer)

        messages = [{"role": "system", "content": SYSTEM}]

        if history:
            for h in history[-6:]:
                if h.get("user_message") and h["user_message"] not in ["[IMAGE]", "[VOICE]"]:
                    messages.append({"role": "user", "content": h["user_message"]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"]})

        user_content = f"शेतकरी: {city}, {district} | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ माहिती:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"
        messages.append({"role": "user", "content": user_content})

        ans = await _cerebras_call(messages, 600)
        if not ans:
            log.warning("Cerebras failed → Groq fallback")
            ans = await _groq_call(messages, 600)
        if not ans:
            return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

        return ans

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

async def disease_detect(image_bytes: bytes, caption: str, farmer: dict) -> str:
    if not image_bytes:
        return "❌ फोटो मिळाला नाही. पुन्हा पाठवा. 📸"
    try:
        import io, base64
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGB": img = img.convert("RGB")
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        crops = ", ".join(farmer.get("crops", [])) or "सांगितले नाही"

        # Sagle disease knowledge context madhe de — photo madhe konte pik te AI ओळखेल
        context = "\n\n".join([
            KNOWLEDGE["onion_disease"], KNOWLEDGE["tomato_disease"],
            KNOWLEDGE["cotton_disease"], KNOWLEDGE["soybean_disease"],
            KNOWLEDGE["grape_disease"], KNOWLEDGE["pomegranate_disease"],
            KNOWLEDGE["potato_disease"], KNOWLEDGE["chilli_disease"],
            KNOWLEDGE["brinjal_disease"], KNOWLEDGE["pest_control"],
        ])

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.2-11b-vision-preview",
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": f"""तू KrishiMitra आहेस — अनुभवी कृषी रोग तज्ञ.

संदर्भ:
{context}

फोटो नीट बघ आणि मराठीत सांग:

📸 फोटो विश्लेषण

संभाव्य समस्या: [नाव सांग]
विश्वास: उच्च / मध्यम / कमी

📌 दिसणारी लक्षणे:
- [काय दिसतं ते सांग]

✅ पुढील उपाय:
- औषध: [brand name सहित]
- dose: 15 लिटर पंपाला [किती]
- कधी फवारायचे: [वेळ]

⚠️ काळजी:
- [महत्त्वाची सूचना]

शेतकरी {crops} घेतो. {f'शेतकरी म्हणतो: {caption}' if caption else ''}
फोटो नीट दिसत नसेल → "अधिक जवळून, प्रकाशात फोटो पाठवा" सांग."""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    "max_tokens": 500,
                    "temperature": 0.1
                }
            )
        if r.status_code == 200:
            d = r.json()["choices"][0]["message"]["content"].strip()
            return f"{d}\n\n📞 _कृषी हेल्पलाइन: 1800-180-1551 (मोफत)_"
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": [], "city": "Pune", "district": "Pune"})

async def voice_to_text(audio_bytes: bytes) -> str:
    if not GROQ_API_KEY or not audio_bytes: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": ("audio.ogg", audio_bytes, "audio/ogg")},
                data={"model": "whisper-large-v3", "language": "mr", "response_format": "text"}
            )
            if r.status_code == 200: return r.text.strip()
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
