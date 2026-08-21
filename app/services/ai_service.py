import logging
import httpx
from app.config import GROQ_API_KEY, TAVILY_API_KEY, GEMINI_API_KEY

log = logging.getLogger(__name__)

GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
# Google cha OpenAI-compatible endpoint — मूळ Groq call cha ekach pattern vaparta yeto,
# vegळा SDK lagत nahi. Free tier: 15 RPM, 250,000 TPM, 1000 RPD — Groq peksha 31 पट जास्त
# tokens/minute, ani Marathi sathi खूप जास्त अचूक. Card lagत nahi.
# टीप: Cerebras (payment-required issue मुळे) पूर्णपणे काढून टाकलाय — फक्त Gemini + Groq वापरतोय.
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GROQ_MODEL     = "openai/gpt-oss-120b"
GEMINI_MODEL   = "gemini-2.5-flash-lite"

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

    "fertilizer_grape": """द्राक्ष खत वेळापत्रक:

लागवड वेळी: शेणखत 10 टन/एकर + DAP 100kg/एकर + Potash 50kg/एकर
15 दिवसांनी: Urea 25kg/एकर — 15L पंपाला नाही, थेट जमिनीत
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g
45 दिवसांनी: Potash 40kg/एकर — गोडी आणि रंगासाठी
फळधारणा सुरू (मणी सेटिंग): Calcium Nitrate 3g/L + Boron 1g/L — 15L पंपाला 45g+15ml
काढणीपूर्वी: Potash जास्त — 00:00:50 5g/L फवारणी""",

    "fertilizer_pomegranate": """डाळिंब खत वेळापत्रक:

लागवड वेळी: शेणखत 15 टन/एकर + DAP 150kg/एकर + Potash 75kg/एकर
15 दिवसांनी: Urea 30kg/एकर
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g
45 दिवसांनी: Potash 50kg/एकर — फळाचा रंग आणि गोडीसाठी
फळधारणा सुरू: Calcium Nitrate 3g/L + Boron 1g/L — फळं तडकू नये म्हणून
पक्वता जवळ: Potash 00:00:50 5g/L फवारणी""",

    "fertilizer_potato": """बटाटा खत वेळापत्रक:

लागवड वेळी: शेणखत 8 टन/एकर + DAP 100kg/एकर + Potash 100kg/एकर
15 दिवसांनी: Urea 40kg/एकर — कंद वाढीसाठी
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g
45 दिवसांनी: Potash 50kg/एकर — कंदाचा आकार वाढण्यासाठी
कंद धरताना (Tuber initiation): Boron 1g/L फवारणी""",

    "fertilizer_wheat": """गहू खत वेळापत्रक:

पेरणीच्या वेळी: DAP 100kg/एकर + Potash 50kg/एकर + शेणखत 4 टन/एकर
21 दिवसांनी: Urea 50kg/एकर — पहिले पाणी देताना
45 दिवसांनी: Urea 50kg/एकर — दुसरे पाणी देताना (फुटवे फुटताना)
ओंबी येताना: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g""",

    "fertilizer_chilli": """मिरची खत वेळापत्रक:

लागवड वेळी: शेणखत 5 टन/एकर + DAP 100kg/एकर + Potash 50kg/एकर
15 दिवसांनी: Urea 25kg/एकर
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g
फुलोरा सुरू: Calcium Nitrate 3g/L + Boron 1g/L — फूल गळती थांबवण्यासाठी
तोडणी सुरू झाल्यावर: दर तोडणीनंतर हलकं Urea 10kg/एकर""",

    "fertilizer_brinjal": """वांगी खत वेळापत्रक:

लागवड वेळी: शेणखत 5 टन/एकर + DAP 100kg/एकर + Potash 60kg/एकर
15 दिवसांनी: Urea 25kg/एकर
30 दिवसांनी: 19:19:19 खत 5g/L फवारणी — 15L पंपाला 75g
फळधारणा सुरू: Calcium Nitrate 3g/L + Boron 1g/L
नियमित तोडणी सुरू असेल: दर 15 दिवसांनी हलकं Urea 10kg/एकर""",

    "fertilizer_sugarcane": """ऊस खत वेळापत्रक:

लागवड वेळी: शेणखत 10 टन/एकर + DAP 150kg/एकर + Potash 100kg/एकर
30 दिवसांनी: Urea 80kg/एकर
60 दिवसांनी: Urea 80kg/एकर + Potash 50kg/एकर
90 दिवसांनी (मोठी बांधणी आधी): Urea 60kg/एकर — शेवटचा हप्ता
4-5 महिन्यांनी: 19:19:19 5g/L फवारणी ऐच्छिक — जोम वाढवण्यासाठी""",

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

## समजून घे, मग बोल:
शेतकऱ्याचा मेसेज छोटा/तुटक असला तरी (संदर्भ, आधीचं संभाषण वापरून) अर्थ लाव — शब्दशः पकडून टेम्पलेट उत्तर देऊ नकोस.

## माणसासारखं बोल, रोबोटसारखं नाही:
साधा प्रश्न असेल तर साधं, बोलल्यासारखं उत्तर दे — फक्त रोग/खताचा तपशीलवार सल्ला असेल तेव्हाच खालचा format वापर. नाराज शेतकऱ्याची आधी काळजी मान्य कर (उदा. "असं होतंय होय, बघू"). दर वेळी उत्तराची सुरुवात वेगळी ठेव — सारखे तेच शब्द वापरू नकोस. Casual प्रश्नाला casual, छोटं उत्तर दे — format ची सक्ती नाही.

## कधीही Numbered List (1. 2. 3.) देऊ नकोस:
शेतकरी नंबर पाठवतो तेव्हा गोंधळ होतो. त्याऐवजी सरळ प्रश्न विचार: "कोणत्या पिकाला समस्या आहे? पानांवर डाग, किडे, की झाड वाळतंय?"

## भाषा शैली:
- Formal/इंग्रजी संज्ञा नको — साधी भाषा (उदा. "Purple Blotch" नाही, "पानावर जांभळे डाग — करपा रोग" असं)
- औषधाचं brand name सांग (उदा. "Mancozeb — Dithane M-45 नावाने मिळतं")
- Dose नेहमी 15 लिटर पंपाच्या प्रमाणात, एकरमध्ये (hectare नाही)
- अनुभवी काकांसारखा टोन — कधीही "As an AI" म्हणू नकोस

## सर्व पिकं समान — कधीही कांदा/टोमॅटो default गृहीत धरू नकोस:
आंबा, ज्वारी, हळद, संत्री, सफरचंद — कुठलंही पीक तितकंच महत्त्वाचं. Farmer कोणत्या पिकाबद्दल बोलतोय ते आधी ओळख.

**History चा आदर कर:** मागच्या संदेशांत पीक/समस्या आधीच ठरली असेल आणि farmer आता "अजून काय करावे", "ते झालं नाही" असं generic follow-up विचारत असेल — तर तोच आधीचा विषय आहे असं गृहीत धर, पुन्हा "कोणत्या पिकाला?" विचारू नकोस.

**पीक विचार फक्त तेव्हा** जेव्हा current message आणि history दोन्हीत पीक सापडत नाही (context रिकामा असणं हे त्याचं संकेत आहे). कधीही अंदाजाने कांदा/टोमॅटो गृहीत धरू नकोस किंवा उदाहरण म्हणून सुचवू नकोस.

एकाच वेळी 2-3 पिकं नाव घेतली असतील तर प्रत्येकाचं उत्तर वेगळं, स्पष्ट दे — एकत्र मिसळू नकोस.

## उत्तर लांबी: 80-100 शब्द कमाल — शक्य तितकं थोडक्यात, नेमकं. फक्त विचारलेल्या प्रश्नाचंच उत्तर, एकच मुख्य उपाय — सगळे पर्याय list करू नकोस, extra स्पष्टीकरण नको.

## Format — फक्त रोग/खत सल्ल्यासाठी:
रोग: 🔍 समस्या 📌 लक्षणे ✅ उपाय (exact dose, 15L पंप) ⚠️ काळजी
खत: 🌱 कोणतं खत 📌 किती (एकर+15L पंप) ⚠️ काळजी
बाकी वेळी (गप्पा, हवामान/भाव, follow-up, धन्यवाद) — नैसर्गिक भाषेत, format ची सक्ती नाही.

## कुठल्याही पिकाला उत्तर दे — फक्त ठराविक यादीतल्या पिकांनाच नाही:
संदर्भात exact माहिती नसेल तरी "माहिती नाही" म्हणून थांबू नकोस — तुझ्या agronomy knowledge ने best-effort, प्रामाणिक उत्तर दे.

## Safety व Accuracy:
"हे औषध नक्की काम करेल" असं कधीही नाही — "फायदेशीर ठरू शकते" म्हण. पडताळलेली माहिती असेल तर शेवटी "🎯 अचूकता: उच्च", स्वतःच्या ज्ञानावरून असेल तर "🎯 अचूकता: मध्यम — कृषी सेवा केंद्रात खात्री करा". फक्त पूर्ण non-farming प्रश्नासाठीच deflect कर ("कृषी केंद्राला विचारा/1800-180-1551") — शेती/पीक/जनावरं/बाजार याबद्दल काहीही असो, उत्तर देण्याचा प्रयत्न कर.

## भाषा: नेहमी मराठीत, साध्या शब्दात, bullet points (paragraphs नको).

शेतकऱ्याला वाटलं पाहिजे तो अनुभवी, जवळच्या माणसाशी बोलतोय.

## इंटरनेट माहिती असेल तर:
- इंटरनेट माहिती: label असलेली माहिती वापर
- Latest/verified information म्हणून treat कर
- Brand names आणि doses confirm कर
- जर internet माहिती आणि KNOWLEDGE dict conflict करत असेल → KNOWLEDGE dict ला priority दे"""

# ── Intent Detection Keywords ──────────────────────────────────────────────
DISEASE_WORDS = [
    "rog", "dag", "blight", "fungus", "karpa", "kida", "kid", "pest", "disease",
    "kirda", "piwla", "black", "pivla", "ali", "al्या", "insect", "spray", "fawarni", "फवारणी",
    "मरतंय", "मरत", "सुकतंय", "सुकत", "वाकडं", "वाकड", "काळं", "काळ", "तपकिरी", "गळतंय", "गळत", "कुजतंय", "कुजत",
    "पिवळं", "पिवळ", "पांढरं", "पांढर", "डाग", "छिद्र", "अळी", "अळ", "किडा", "किड", "किडे", "बुरशी", "बुरश",
    "करपा", "मर ", "व्हायरस", "virus", "रोग",
    "marat", "sukhat", "vakat", "kharab", "chidra", "pivla",
    "galat", "kujat", "pane", "pale", "yellow", "white", "brown",
    "problem", "trouble", "kahi zala", "hotat", "zalay", "kharab zala"
]

FERTILIZER_WORDS = [
    "khad", "khata", "khate", "fertilizer", "urea", "npk", "poshan",
    "dap", "potash", "zinc", "boron", "nutrients", "khaychi",
    "वाढत", "वाढ", "लहान", "खत", "खता", "पोषण", "खुजा", "खुरटल",
    "vadhat", "lahan", "khuja", "grow", "growth", "dose", "डोस", "मात्रा"
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
# NOTE: "KB_CROPS" cha KNOWLEDGE dict madhe specific disease/fertilizer entries aahet.
# Khalcha "OTHER_CROPS" fakt naव ओळखण्यासाठी — tyanchya sathi generic + web-search based उत्तर banat.
# टीप: Marathi madhe pratyay (ला/चं/चा/ने) lagla ki mool shabd badalto
# (उदा. कांदा→कांद्याला, गहू→गव्हाला, वांगे→वांग्याला). म्हणून प्रत्येक पिकासाठी
# root + declined (oblique) forms दोन्ही dilay, nahitar farmer ne "कांद्याला" lihila
# tar "कांदा" keyword match hot nahi ani crop olakhla jat nahi.
KB_CROPS = {
    "onion":     ["onion", "kanda", "kandya", "कांदा", "कांद्या", "पयाज"],
    "tomato":    ["tomato", "tamatar", "टोमॅटो", "टोमॅट्या"],
    "cotton":    ["cotton", "kapus", "kapas", "कापूस", "कापस", "कापशी"],
    "soybean":   ["soybean", "soya", "सोयाबीन"],
    "grape":     ["grape", "draksha", "द्राक्ष"],
    "pomegranate": ["pomegranate", "dalimb", "anar", "डाळिंब"],
    "potato":    ["potato", "batata", "बटाटा", "बटाट्या"],
    "wheat":     ["wheat", "gahu", "gavha", "गहू", "गव्ह"],
    "chilli":    ["chilli", "mirchi", "मिरची"],
    "brinjal":   ["brinjal", "vange", "वांगी", "वांगे", "वांग्या", "वांग"],
    "sugarcane": ["sugarcane", "us", "ऊस", "उस", "उसा"],
}

OTHER_CROPS = {
    "mango":       ["mango", "amba", "aamba", "आंबा", "आंबे", "आंब्या", "आंब"],
    "banana":      ["banana", "kela", "kele", "केळी", "केळ", "केळ्या"],
    "orange":      ["orange", "santra", "narangi", "संत्रा", "संत्र्या", "मोसंबी", "mosambi"],
    "coconut":     ["coconut", "naral", "नारळ"],
    "jowar":       ["jowar", "jvari", "ज्वारी"],
    "bajra":       ["bajra", "bajri", "बाजरी"],
    "maize":       ["maize", "corn", "makka", "मका", "मक्या"],
    "tur":         ["tur", "arhar", "तूर", "तुर", "तूरडाळ"],
    "moong":       ["moong", "mug", "मूग", "मुग"],
    "udid":        ["udid", "urad", "उडीद", "उडद"],
    "harbara":     ["harbara", "chana", "chickpea", "हरभरा", "हरभऱ्या"],
    "groundnut":   ["groundnut", "bhuimug", "shengdana", "भुईमूग", "भुईमुग", "शेंगदाणा"],
    "turmeric":    ["turmeric", "halad", "हळद"],
    "ginger":      ["ginger", "aale", "आले", "आलं", "आल्याला", "आल्याचं"],
    "cabbage":     ["cabbage", "kobi", "कोबी"],
    "cauliflower": ["cauliflower", "phulkobi", "फ्लॉवर"],
    "okra":        ["okra", "bhendi", "bhindi", "भेंडी"],
    "cucumber":    ["cucumber", "kakadi", "काकडी"],
    "guava":       ["guava", "peru", "पेरू", "पेरु"],
    "papaya":      ["papaya", "papai", "पपई"],
    "watermelon":  ["watermelon", "kalingad", "कलिंगड"],
    "sunflower":   ["sunflower", "suryaphool", "सूर्यफूल", "सूर्यफुल"],
    "mustard":     ["mustard", "mohri", "मोहरी"],
    "safflower":   ["safflower", "karale", "करडई"],
    "castor":      ["castor", "erandi", "एरंडी"],
    "sesame":      ["sesame", "til", "तीळ", "तिळ"],
    "flower":      ["marigold", "zendu", "झेंडू", "gulab", "गुलाब", "फुलशेती"],
    "apple":       ["apple", "safarchand", "सफरचंद", "सफरचंदा"],
    "strawberry":  ["strawberry", "स्ट्रॉबेरी"],
    "fig":         ["fig", "anjeer", "अंजीर"],
    "custard_apple": ["custard apple", "sitaphal", "सीताफळ"],
    "lemon":       ["lemon", "limbu", "लिंबू"],
    "drumstick":   ["drumstick", "shevga", "शेवगा"],
    "gram":        ["moth", "matki", "मटकी"],
}

# CROP_KEYWORDS = combined — message_handler.py cha crop-save logic sathi vaparla jato
CROP_KEYWORDS = {**KB_CROPS, **OTHER_CROPS}

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

_DISEASE_MAP = {
    "onion": "onion_disease", "tomato": "tomato_disease",
    "cotton": "cotton_disease", "soybean": "soybean_disease",
    "grape": "grape_disease", "pomegranate": "pomegranate_disease",
    "potato": "potato_disease", "wheat": "wheat_disease",
    "chilli": "chilli_disease", "brinjal": "brinjal_disease",
    "sugarcane": "sugarcane_disease",
}
_FERT_MAP = {
    "onion": "fertilizer_onion", "tomato": "fertilizer_tomato",
    "cotton": "fertilizer_cotton", "soybean": "fertilizer_soybean",
    "grape": "fertilizer_grape", "pomegranate": "fertilizer_pomegranate",
    "potato": "fertilizer_potato", "wheat": "fertilizer_wheat",
    "chilli": "fertilizer_chilli", "brinjal": "fertilizer_brinjal",
    "sugarcane": "fertilizer_sugarcane",
}

def _infer_crop_from_history(history: list) -> list:
    """Current question madhe crop mention nasel (उदा. follow-up: 'ajun konte upay karave',
    'te zala nahi') tar — sarvat अलीकडच्या 2-3 messages madhun konta pik discuss hot hota
    te olakh. Hे khoop mahatvach — nahitar agent parat parat 'kontya pikala' vicharat rahto
    ani farmer la vatta ki tyani adhi vicharlele agent la aathvatach nahi."""
    if not history:
        return []
    for h in reversed(history[-3:]):  # सर्वात अलीकडचा turn आधी check कर
        combined = f"{h.get('user_message','') or ''} {h.get('bot_response','') or ''}"
        crops = _detect_crops(combined, [])
        if crops:
            return crops
    return []

def _get_context(question: str, farmer: dict, history: list = None) -> tuple:
    """Returns (context_str, specific_kb_found: bool, unmapped_crops: list)
    specific_kb_found=False means — active_crops OLakhle gele, pan KNOWLEDGE dict madhe
    tyanchi specific entry nahi (उदा. आंबा, ज्वारी) → asha veli web search FORCE karaycha
    ani LLM la स्वतःच्या ज्ञानाने उत्तर द्यायला सांगायचं (deflect न करता)."""
    q = question.lower()

    # टीप: प्रत्येक वेळी crop EXPLICIT हवा — current message मध्ये किंवा conversation
    # history मध्ये. farmer.crops (जो database चा DEFAULT placeholder ['onion','tomato']
    # असतो, farmer ने कधीच confirm केलेला नसतो) इथे कधीच गृहीत धरायचा नाही — नाहीतर
    # प्रत्येक अस्पष्ट प्रश्नाला आपोआप "कांदा/टोमॅटो" उत्तर जातं, जे चुकीचं आणि गोंधळात टाकणारं आहे.
    explicit_crops = _detect_crops(question, [])
    active_crops = explicit_crops
    inferred_from_history = False
    if not active_crops and history:
        active_crops = _infer_crop_from_history(history)
        if active_crops:
            inferred_from_history = True

    # पीक कुठेच सापडलं नाही (ना current message, ना history) — तर farmer.crops वर अंदाज
    # घेऊन उत्तर देऊ नकोस. मॉडेलला थेट विचारू दे "कोणत्या पिकाबद्दल आहे?"
    if not active_crops:
        return "", False, []

    parts = []
    specific_found = False
    unmapped = []
    topic_matched = False

    if any(w in q for w in DISEASE_WORDS):
        topic_matched = True
        if len(active_crops) > 1:
            for crop in active_crops:
                key = _DISEASE_MAP.get(crop)
                if key and KNOWLEDGE.get(key):
                    parts.append(f"--- {crop.upper()} साठी माहिती ---\n{KNOWLEDGE[key]}")
                    specific_found = True
                elif crop in OTHER_CROPS:
                    unmapped.append(crop)
        else:
            for crop in active_crops:
                key = _DISEASE_MAP.get(crop)
                if key and KNOWLEDGE.get(key):
                    parts.append(KNOWLEDGE[key])
                    specific_found = True
                elif crop in OTHER_CROPS:
                    unmapped.append(crop)
        parts.append(KNOWLEDGE["pest_control"])

    if any(w in q for w in FERTILIZER_WORDS):
        topic_matched = True
        for crop in active_crops:
            key = _FERT_MAP.get(crop)
            if key and KNOWLEDGE.get(key):
                parts.append(KNOWLEDGE[key])
                specific_found = True
            elif crop in OTHER_CROPS and crop not in unmapped:
                unmapped.append(crop)

    if any(w in q for w in SEASON_WORDS):
        topic_matched = True
        parts.append(KNOWLEDGE["seasonal_calendar"])
        specific_found = True

    if any(w in q for w in WATER_WORDS):
        topic_matched = True
        parts.append(KNOWLEDGE["irrigation"])
        specific_found = True

    if any(w in q for w in SCHEME_WORDS):
        topic_matched = True
        parts.append(KNOWLEDGE["government_schemes"])
        specific_found = True

    # Follow-up case — history वरून crop मिळाला (current message मध्ये topic keyword
    # नसतानाही, उदा. "ajun konte upay karave"): हे आधीच्याच विषयाची निरंतरता आहे,
    # त्यामुळे त्या crop चं disease+fert KB देणं योग्य.
    if inferred_from_history and not topic_matched:
        for crop in active_crops:
            d_key = _DISEASE_MAP.get(crop)
            f_key = _FERT_MAP.get(crop)
            if d_key and KNOWLEDGE.get(d_key) and KNOWLEDGE[d_key] not in parts:
                parts.append(KNOWLEDGE[d_key]); specific_found = True
            if f_key and KNOWLEDGE.get(f_key) and KNOWLEDGE[f_key] not in parts:
                parts.append(KNOWLEDGE[f_key]); specific_found = True
            if crop in OTHER_CROPS and crop not in unmapped:
                unmapped.append(crop)

    # टीप: topic कुठल्याच ओळखीच्या category मध्ये बसत नसेल (disease/fert/water/season/
    # scheme नाही) आणि हा follow-up सुद्धा नाही — म्हणजे शेतकऱ्याने काहीतरी वेगळंच विचारलंय
    # (उदा. "कांदा कधी काढायचा", "बाजारभाव कसा ठरतो"). अशा वेळी चुकीचा disease+fert dump
    # देण्याऐवजी context रिकामा सोड — यामुळे आपोआप web search trigger होईल आणि खऱ्या
    # प्रश्नाला संबंधित उत्तर मिळेल, ऐवजी नेहमी रोग/खताची माहिती चिकटवण्याऐवजी.
    if not topic_matched and not inferred_from_history:
        for crop in active_crops:
            if crop not in unmapped:
                unmapped.append(crop)
        return "", False, unmapped

    return "\n\n".join(parts), specific_found, unmapped

# ── API Calls ──────────────────────────────────────────────────────────────
import re

def _clean_llm_output(text: str) -> str:
    """gpt-oss (Harmony format) chya kadhi-kadhi chukun leak hoणाऱ्या internal control
    tokens (<|start|>, <|channel|>, <|return|> वगैरे) काढून टाकतो — high reasoning_effort
    वापरताना हा risk जरा वाढतो, त्यामुळे farmer ला कधीच tuटलेलं/raw output दिसू नये यासाठी safety net."""
    if not text:
        return text
    text = re.sub(r"<\|[a-zA-Z_]+\|>", "", text)
    return text.strip()

async def _gemini_call(messages: list, max_tokens: int = 600) -> str:
    """Google Gemini — OpenAI-compatible endpoint वापरून, त्यामुळे Cerebras/Groq सारखाच
    call pattern. Free tier: 15 RPM, 250,000 TPM (Groq पेक्षा 31 पट जास्त), 1000 RPD.
    Card लागत नाही — aistudio.google.com वर मोफत key मिळते."""
    if not GEMINI_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GEMINI_URL,
                headers={"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"},
                json={"model": GEMINI_MODEL, "messages": messages, "max_tokens": max_tokens,
                      "temperature": 0.4}
            )
            if r.status_code == 200:
                return _clean_llm_output(r.json()["choices"][0]["message"]["content"])
            log.error(f"Gemini: {r.status_code} {r.text[:150]}")
            return ""
    except Exception as e:
        log.error(f"Gemini failed: {e}")
        return ""

async def _groq_call(messages: list, max_tokens: int = 600) -> str:
    if not GROQ_API_KEY: return ""
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": GROQ_MODEL, "messages": messages, "max_tokens": max_tokens,
                      "temperature": 0.4, "reasoning_effort": "low", "include_reasoning": False}
            )
            if r.status_code == 200:
                return _clean_llm_output(r.json()["choices"][0]["message"]["content"])
            log.error(f"Groq: {r.status_code}")
            return ""
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return ""

# ── Tavily Web Search (fallback when KNOWLEDGE dict has no answer) ─────────
_WEB_SEARCH_TRIGGER_WORDS = [
    "नवीन", "latest", "2024", "2025", "2026", "नुकताच", "आत्ता",
    "new", "recent", "current", "ताजे", "अद्ययावत"
]

# Tavily results cache — same crop/topic combo boarबार search करायची गरज नाही (in-memory,
# server restart झाला की रिकामा होतो — पण अजूनही मोठ्या प्रमाणात duplicate searches वाचतात,
# कारण बरेच शेतकरी सिझनल/सारख्याच समस्यांबद्दल विचारतात).
_tavily_cache: dict = {}
_TAVILY_CACHE_TTL = 43200  # 12 तास (सेकंदात)

async def _tavily_search(query: str) -> str:
    """Tavily web search — फक्त KNOWLEDGE dict madhe answer nasel tevhach call hoto.
    टीप: search_depth='basic' वापरतो (1 credit) 'advanced' (2 credits) ऐवजी — free tier
    (1000 credits/month) दुप्पट काळ टिकतो. + 12-तास cache मुळे same query परत परत
    charge होत नाही."""
    if not TAVILY_API_KEY:
        return ""
    import time
    cache_key = query.strip().lower()
    cached = _tavily_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _TAVILY_CACHE_TTL:
        log.info(f"Tavily cache hit: {cache_key[:50]}")
        return cached[1]
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        search_query = f"{query} उपाय Maharashtra शेती मराठी"
        result = client.search(
            query=search_query,
            search_depth="basic",
            max_results=2
        )
        items = result.get("results", [])
        if not items:
            return ""
        combined = "\n\n".join([
            f"{item.get('title', '')}: {item.get('content', '')[:200]}"
            for item in items[:2]
        ])
        log.info(f"Tavily search success: {search_query[:50]}")
        _tavily_cache[cache_key] = (time.time(), combined)
        # Cache जास्त मोठा होऊ नये म्हणून जुनी entries साफ कर
        if len(_tavily_cache) > 500:
            oldest = sorted(_tavily_cache.items(), key=lambda x: x[1][0])[:100]
            for k, _ in oldest:
                _tavily_cache.pop(k, None)
        return combined
    except Exception as e:
        log.error(f"Tavily search failed: {e}")
        return ""

async def _needs_web_search(question: str, context: str, specific_found: bool, unmapped_crops: list) -> bool:
    """KNOWLEDGE dict madhe accurate answer nasel tarच web search karaycha — quota vachvaycha.
    specific_found=False (crop KB madhe nahi, e.g. आंबा/ज्वारी) किंवा context रिकामा असेल
    तर FORCE search — nahitar agent generic/चुकीचं उत्तर देईल."""
    if not context or not context.strip():
        return True
    if not specific_found:
        return True
    if unmapped_crops:
        return True
    q_lower = question.lower()
    if any(w in q_lower for w in _WEB_SEARCH_TRIGGER_WORDS):
        return True
    return False

def _build_tavily_query(question: str, farmer_crops: list) -> str:
    """Smart query banav — crop + problem + Maharashtra"""
    crops_str = " ".join(farmer_crops) if farmer_crops else ""
    if crops_str:
        return f"{crops_str} {question}"
    return question

async def farming_answer(question: str, farmer: dict, history: list = None) -> str:
    if not GEMINI_API_KEY and not GROQ_API_KEY:
        return "❌ सेवा सध्या उपलब्ध नाही. थोड्या वेळाने विचारा. 🙏"
    try:
        farmer_crops = farmer.get("crops", [])
        crops = ", ".join(farmer_crops) or "सांगितले नाही"
        city = farmer.get("city", "Pune")
        district = farmer.get("district", "Pune")
        context, specific_found, unmapped_crops = _get_context(question, farmer, history)

        # टीप: तीन केसेस वेगळ्या ओळखतो — पुढे Tavily आणि prompt दोन्हीसाठी वापरायला:
        # 1) is_ambiguous — कुठलंच पीक ओळखलं गेलं नाही (ना message, ना history) → Tavily
        #    call करायचाच नाही (कशाबद्दल search करणार?) — model ला थेट विचारू दे.
        # 2) specific_found False + unmapped_crops आहे — पीक माहीत, KB मध्ये नाही → search कर
        # 3) specific_found True — verified माहिती आधीच आहे
        is_ambiguous = (not specific_found) and (not unmapped_crops) and (not context.strip())

        # Follow-up question आहे का — म्हणजे current message madhe crop mention nasla,
        # pan history madhun tो olakhla gela. Asel tar model la explicit sanga, nahitar
        # tо parat "kontya pikala?" vicharat rahil (jari history var vishayacha context asel tari).
        current_msg_crops = _detect_crops(question, [])
        inferred_crop_note = ""
        if not current_msg_crops and history:
            inferred = _infer_crop_from_history(history)
            if inferred:
                inferred_crop_note = (
                    f"\n\n[सूचना: शेतकऱ्याने या मेसेजमध्ये पिकाचं नाव घेतलेलं नाही, पण वरच्या "
                    f"संभाषणावरून हे स्पष्ट आहे की तो **{', '.join(inferred)}** बद्दलच पुढे विचारतोय — "
                    f"तेच पीक गृहीत धर आणि थेट उत्तर दे. पुन्हा 'कोणत्या पिकाला?' विचारू नकोस.]"
                )

        # Tavily web search — KNOWLEDGE dict madhe accurate/specific answer nasel tarच.
        # is_ambiguous असेल तर कधीच call करू नकोस — पीकच माहीत नसताना search केला तर
        # farmer_crops chya DEFAULT (कांदा/टोमॅटो) वर आधारित चुकीचा search होतो, आणि उगाच
        # Tavily quota (1000 credits/month) वाया जातो.
        needs_search = (not is_ambiguous) and await _needs_web_search(question, context, specific_found, unmapped_crops)
        if TAVILY_API_KEY and needs_search:
            tavily_query = _build_tavily_query(question, unmapped_crops or current_msg_crops)
            web_info = await _tavily_search(tavily_query)
            if web_info:
                context = (context + f"\n\nइंटरनेट माहिती:\n{web_info}").strip()
                specific_found = True

        messages = [{"role": "system", "content": SYSTEM}]

        # टीप: history madhle june bot-answers kadhi kadhi lambe astat (250+ shabda).
        # ते जसेच्या तसे परत पाठवले तर context खूप मोठा होतो — free-tier token
        # quota (Cerebras/Groq) वर अनावश्यक ताण पडतो. म्हणून प्रत्येक जुना संदेश थोडक्यात कापतो —
        # crop/topic ओळखण्यासाठी हे पुरेसं आहे, पूर्ण जुनं उत्तर परत पाठवायची गरज नाही.
        # टीप: Cerebras सध्या payment-required मुळे बंद आहे → 100% भार Groq वर (फक्त
        # 8,000 tokens/minute free tier). त्यामुळे history/tokens शक्य तितकं कमी ठेवलंय —
        # Cerebras परत सुरू झाल्यावर हे परत वाढवता येईल.
        _HISTORY_CHAR_CAP = 180
        if history:
            for h in history[-3:]:
                if h.get("user_message") and h["user_message"] not in ["[IMAGE]", "[VOICE]"]:
                    messages.append({"role": "user", "content": h["user_message"][:_HISTORY_CHAR_CAP]})
                if h.get("bot_response"):
                    messages.append({"role": "assistant", "content": h["bot_response"][:_HISTORY_CHAR_CAP]})

        user_content = f"शेतकरी: {city}, {district} | पिके: {crops}"
        if context:
            user_content += f"\n\nसंदर्भ माहिती:\n{context}"
        user_content += f"\n\nप्रश्न: {question}"
        user_content += inferred_crop_note

        # टीप: तीन वेगळ्या केसेस — प्रत्येकीला वेगळी सूचना हवी:
        # 1) प्रश्न खूप त्रोटक/अस्पष्ट (कुठलंच पीक/लक्षण सापडलं नाही) → अंदाज नको, नीट प्रश्न विचार
        # 2) पीक ओळखलं पण आपल्या KB मध्ये specific माहिती नाही (उदा. आंबा) → best-effort उत्तर दे
        # 3) पीक + KB दोन्ही सापडलं → verified उत्तर दे
        is_ambiguous = (not specific_found) and (not unmapped_crops) and (not context.strip())

        # टीप: हे 1 ओळीचं log — पुढच्या आठवड्यात keyword-matching किती वेळा चुकतंय ते
        # प्रत्यक्ष मोजण्यासाठी. Render च्या Logs tab मध्ये "ROUTING_STATS" search कर —
        # ambiguous किती % आहे ते बघून ठरव tool-calling कडे जायचं का.
        route = "AMBIGUOUS" if is_ambiguous else ("UNMAPPED_CROP" if unmapped_crops else ("KB_HIT" if specific_found else "OTHER"))
        log.info(f"ROUTING_STATS | route={route} | q_words={len(question.split())} | crops={unmapped_crops or 'known'}")

        if is_ambiguous:
            user_content += (
                "\n\n[सूचना: शेतकऱ्याचा प्रश्न खूप त्रोटक/अस्पष्ट आहे — कुठलं पीक, कुठला भाग "
                "(पान/खोड/फळ/मूळ), काय लक्षण याबद्दल काहीच स्पष्ट नाही. अंदाजाने उत्तर देऊ नकोस — "
                "त्याला थोडक्यात, नैसर्गिक भाषेत विचार की नेमकं काय विचारायचंय (उदा. 'कोणत्या पिकाला "
                "समस्या आहे आणि नक्की काय दिसतंय — पान पिवळी, डाग, किडे?'). एकाच वेळी एकच प्रश्न विचार. "
                "अचूकता टॅग लिहू नकोस — अजून उत्तरच दिलेलं नाहीये.]"
            )
        elif not specific_found:
            user_content += (
                "\n\n[सूचना: वरील संदर्भात या प्रश्नाचं exact answer नाही. तरी तुझ्या स्वतःच्या "
                "कृषी ज्ञानाने प्रामाणिक, practical उत्तर दे — टाळू नकोस किंवा फक्त 'कृषी केंद्राला विचारा' "
                "असं म्हणून थांबू नकोस. उत्तराच्या शेवटी एका ओळीत 🎯 अचूकता: मध्यम — असं लिही आणि "
                "जवळच्या कृषी सेवा केंद्र/1800-180-1551 वर खात्री करायला सांग.]"
            )
        else:
            user_content += "\n\n[उत्तराच्या शेवटी एका ओळीत 🎯 अचूकता: उच्च — असं लिही, कारण ही माहिती पडताळलेल्या स्रोतातून आहे.]"

        messages.append({"role": "user", "content": user_content})

        # टीप: Cerebras सध्या पूर्ण बंद केलंय (payment-required issue) — chain मधून काढलंय,
        # वेळ वाया जात नाही (आधी fail होऊन मग पुढच्याकडे जायला लागायचा वेळ आता वाचतो).
        # Gemini (primary, 250K TPM free) → Groq (fallback, 8K TPM free) — फक्त दोनच पुरेसे आहेत.
        ans = await _gemini_call(messages, 250)
        if not ans:
            log.warning("Gemini failed → Groq fallback")
            ans = await _groq_call(messages, 250)
        if not ans:
            return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

        return ans

    except Exception as e:
        log.error(f"farming_answer: {e}")
        return "❌ थोडी अडचण आली. पुन्हा विचारा. 🙏"

_DISEASE_KB_MAP = {
    "onion": "onion_disease", "tomato": "tomato_disease",
    "cotton": "cotton_disease", "soybean": "soybean_disease",
    "grape": "grape_disease", "pomegranate": "pomegranate_disease",
    "potato": "potato_disease", "wheat": "wheat_disease",
    "chilli": "chilli_disease", "brinjal": "brinjal_disease",
    "sugarcane": "sugarcane_disease",
}

def _identify_photo_crop(caption: str, farmer_crops: list) -> list:
    """Caption ani farmer.crops वरून konta pik असेल ओळखण्याचा प्रयत्न — ओळखलं तरच specific KB धाडतो"""
    text = (caption or "").lower()
    found = []
    for crop, keywords in CROP_KEYWORDS.items():
        if any(k in text for k in keywords):
            found.append(crop)
    if found:
        return found
    if farmer_crops:
        normalized = [c.lower() for c in farmer_crops if c.lower() in _DISEASE_KB_MAP]
        if len(normalized) == 1:
            return normalized
    return []  # unidentified — sagla KB pathav

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
        farmer_crops = farmer.get("crops", [])
        crops = ", ".join(farmer_crops) or "सांगितले नाही"

        # Crop ओळखण्याचा प्रयत्न — ओळखलं तर फक्त त्याच पिकाचं KB, नाहीतर सगळं (current behavior)
        identified = _identify_photo_crop(caption, farmer_crops)
        if identified:
            kb_keys = [_DISEASE_KB_MAP[c] for c in identified if c in _DISEASE_KB_MAP]
            context = "\n\n".join([KNOWLEDGE[k] for k in kb_keys] + [KNOWLEDGE["pest_control"]])
        else:
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
                    "model": "qwen/qwen3.6-27b",
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
            result = f"{d}\n\n📞 _कृषी हेल्पलाइन: 1800-180-1551 (मोफत)_"
            # Low confidence असेल तर specific re-take instructions जोड
            if "विश्वास: कमी" in d or "confidence: low" in d.lower():
                result += ("\n\n📸 फोटो नीट दिसला नाही. कृपया:\n"
                           "• उजेडात फोटो काढा\n"
                           "• पानाच्या जवळून फोटो काढा\n"
                           "• रोगग्रस्त भाग स्पष्ट दिसू द्या\n"
                           "आणि पुन्हा पाठवा 🙏")
            return result
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"
    except Exception as e:
        log.error(f"disease_detect: {e}")
        return "❌ फोटो तपासता आला नाही. स्वच्छ फोटो पाठवा. 🙏"

async def scheme_info(query: str) -> str:
    return await farming_answer(query, {"crops": [], "city": "Pune", "district": "Pune"})

_VOICE_CORRECTIONS = {
    "कापसा": "कापूस", "सोयाबिन": "सोयाबीन", "टमाटर": "टोमॅटो",
    "कांदे": "कांदा", "मिरच्या": "मिरची", "वांगी": "वांगे",
}

def _normalize_voice_text(text: str) -> str:
    """Whisper cha common Marathi crop-name chukasathi normalize kar"""
    for wrong, correct in _VOICE_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text

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
            if r.status_code == 200:
                return _normalize_voice_text(r.text.strip())
            return ""
    except Exception as e:
        log.error(f"voice_to_text: {e}")
        return ""
