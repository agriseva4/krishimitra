--- original/krishimitra-main/app/services/ai_service.py	2026-07-09 19:21:35.000000000 +0000
+++ krishimitra-main/app/services/ai_service.py	2026-08-16 17:32:53.390150735 +0000
@@ -367,9 +367,18 @@
 📌 किती द्यायचे (एकर + 15L पंप)
 ⚠️ काळजी
 
-## Safety:
+## तू सर्व पिकांना उत्तर देतोस — फक्त वरच्या यादीतल्या पिकांनाच नाही:
+आंबा, केळी, ज्वारी, बाजरी, मका, तूर, हरभरा, भुईमूग, हळद, आले, कोबी, संत्री, नारळ,
+फुलशेती — कोणतंही पीक असो, तुला माहिती असलेल्या कृषी ज्ञानाने नेहमी उत्तर दे.
+संदर्भ माहितीत त्या पिकाची exact माहिती नसेल तरी "मला माहिती नाही" म्हणून थांबू नकोस —
+तुझ्या agronomy knowledge वरून best-effort, practical उत्तर दे (पीक कोणतंही असो).
+
+## Safety व Accuracy:
 - "हे औषध नक्की काम करेल" असे कधीही नाही — "हे फायदेशीर ठरू शकते" सांग
-- माहिती नाही → "जवळच्या कृषी केंद्राला विचारा किंवा 1800-180-1551 वर call करा"
+- संदर्भ माहितीतून (पडताळलेलं) उत्तर देत असशील → शेवटी "🎯 अचूकता: उच्च" लिही
+- स्वतःच्या सामान्य ज्ञानातून उत्तर देत असशील (संदर्भात नसेल तर) → शेवटी "🎯 अचूकता: मध्यम — जवळच्या कृषी सेवा केंद्रात खात्री करा" लिही
+- फक्त तेव्हाच पूर्ण deflect कर जेव्हा प्रश्न शेतीशी संबंधितच नसेल (उदा. राजकारण, अनोळखी विषय) — शेती/पीक/जनावरं/बाजार याबद्दल काहीही विचारलं तरी उत्तर देण्याचा प्रयत्न कर, टाळू नकोस
+- सर्व शेती-प्रश्नांना (KB मध्ये असो वा नसो) उत्तर दे; फक्त पूर्णपणे unrelated (non-farming) प्रश्नासाठीच "जवळच्या कृषी केंद्राला विचारा किंवा 1800-180-1551 वर call करा" वापर
 
 ## भाषा:
 - नेहमी मराठीत उत्तर दे, साध्या शब्दात
@@ -385,20 +394,21 @@
 
 # ── Intent Detection Keywords ──────────────────────────────────────────────
 DISEASE_WORDS = [
-    "rog", "dag", "blight", "fungus", "karpa", "kida", "pest", "disease",
-    "kirda", "piwla", "black", "pivla", "ali", "insect", "spray",
-    "मरतंय", "सुकतंय", "वाकडं", "काळं", "तपकिरी", "गळतंय", "कुजतंय",
-    "पिवळं", "पांढरं", "डाग", "छिद्र", "अळी", "किडा", "बुरशी",
+    "rog", "dag", "blight", "fungus", "karpa", "kida", "kid", "pest", "disease",
+    "kirda", "piwla", "black", "pivla", "ali", "al्या", "insect", "spray", "fawarni", "फवारणी",
+    "मरतंय", "मरत", "सुकतंय", "सुकत", "वाकडं", "वाकड", "काळं", "काळ", "तपकिरी", "गळतंय", "गळत", "कुजतंय", "कुजत",
+    "पिवळं", "पिवळ", "पांढरं", "पांढर", "डाग", "छिद्र", "अळी", "अळ", "किडा", "किड", "किडे", "बुरशी", "बुरश",
+    "करपा", "मर ", "व्हायरस", "virus", "रोग",
     "marat", "sukhat", "vakat", "kharab", "chidra", "pivla",
     "galat", "kujat", "pane", "pale", "yellow", "white", "brown",
-    "problem", "trouble", "kahi", "nahi", "hotat", "zalay"
+    "problem", "trouble", "kahi zala", "hotat", "zalay", "kharab zala"
 ]
 
 FERTILIZER_WORDS = [
     "khad", "khata", "khate", "fertilizer", "urea", "npk", "poshan",
     "dap", "potash", "zinc", "boron", "nutrients", "khaychi",
-    "वाढत", "लहान", "खत", "पोषण", "खुजा",
-    "vadhat", "lahan", "khuja", "grow", "growth"
+    "वाढत", "वाढ", "लहान", "खत", "खता", "पोषण", "खुजा", "खुरटल",
+    "vadhat", "lahan", "khuja", "grow", "growth", "dose", "डोस", "मात्रा"
 ]
 
 WATER_WORDS = [
@@ -419,20 +429,59 @@
 ]
 
 # Crop name detection — pratyek pikache keywords
-CROP_KEYWORDS = {
-    "onion":     ["onion", "kanda", "kandya", "कांदा", "पयाज"],
-    "tomato":    ["tomato", "tamatar", "टोमॅटो"],
-    "cotton":    ["cotton", "kapus", "कापूस"],
+# NOTE: "KB_CROPS" cha KNOWLEDGE dict madhe specific disease/fertilizer entries aahet.
+# Khalcha "OTHER_CROPS" fakt naव ओळखण्यासाठी — tyanchya sathi generic + web-search based उत्तर banat.
+# टीप: Marathi madhe pratyay (ला/चं/चा/ने) lagla ki mool shabd badalto
+# (उदा. कांदा→कांद्याला, गहू→गव्हाला, वांगे→वांग्याला). म्हणून प्रत्येक पिकासाठी
+# root + declined (oblique) forms दोन्ही dilay, nahitar farmer ne "कांद्याला" lihila
+# tar "कांदा" keyword match hot nahi ani crop olakhla jat nahi.
+KB_CROPS = {
+    "onion":     ["onion", "kanda", "kandya", "कांदा", "कांद्या", "पयाज"],
+    "tomato":    ["tomato", "tamatar", "टोमॅटो", "टोमॅट्या"],
+    "cotton":    ["cotton", "kapus", "kapas", "कापूस", "कापस", "कापशी"],
     "soybean":   ["soybean", "soya", "सोयाबीन"],
     "grape":     ["grape", "draksha", "द्राक्ष"],
     "pomegranate": ["pomegranate", "dalimb", "anar", "डाळिंब"],
-    "potato":    ["potato", "batata", "बटाटा"],
-    "wheat":     ["wheat", "gahu", "गहू"],
+    "potato":    ["potato", "batata", "बटाटा", "बटाट्या"],
+    "wheat":     ["wheat", "gahu", "gavha", "गहू", "गव्ह"],
     "chilli":    ["chilli", "mirchi", "मिरची"],
-    "brinjal":   ["brinjal", "vange", "वांगी", "वांगे"],
-    "sugarcane": ["sugarcane", "us", "ऊस"],
+    "brinjal":   ["brinjal", "vange", "वांगी", "वांगे", "वांग्या", "वांग"],
+    "sugarcane": ["sugarcane", "us", "ऊस", "उस", "उसा"],
+}
+
+OTHER_CROPS = {
+    "mango":       ["mango", "amba", "aamba", "आंबा", "आंबे", "आंब्या", "आंब"],
+    "banana":      ["banana", "kela", "kele", "केळी", "केळ", "केळ्या"],
+    "orange":      ["orange", "santra", "narangi", "संत्रा", "संत्र्या", "मोसंबी", "mosambi"],
+    "coconut":     ["coconut", "naral", "नारळ"],
+    "jowar":       ["jowar", "jvari", "ज्वारी"],
+    "bajra":       ["bajra", "bajri", "बाजरी"],
+    "maize":       ["maize", "corn", "makka", "मका", "मक्या"],
+    "tur":         ["tur", "arhar", "तूर", "तुर", "तूरडाळ"],
+    "moong":       ["moong", "mug", "मूग", "मुग"],
+    "udid":        ["udid", "urad", "उडीद", "उडद"],
+    "harbara":     ["harbara", "chana", "chickpea", "हरभरा", "हरभऱ्या"],
+    "groundnut":   ["groundnut", "bhuimug", "shengdana", "भुईमूग", "भुईमुग", "शेंगदाणा"],
+    "turmeric":    ["turmeric", "halad", "हळद"],
+    "ginger":      ["ginger", "aale", "आले", "आलं", "आल्याला", "आल्याचं"],
+    "cabbage":     ["cabbage", "kobi", "कोबी"],
+    "cauliflower": ["cauliflower", "phulkobi", "फ्लॉवर"],
+    "okra":        ["okra", "bhendi", "bhindi", "भेंडी"],
+    "cucumber":    ["cucumber", "kakadi", "काकडी"],
+    "guava":       ["guava", "peru", "पेरू", "पेरु"],
+    "papaya":      ["papaya", "papai", "पपई"],
+    "watermelon":  ["watermelon", "kalingad", "कलिंगड"],
+    "sunflower":   ["sunflower", "suryaphool", "सूर्यफूल", "सूर्यफुल"],
+    "mustard":     ["mustard", "mohri", "मोहरी"],
+    "safflower":   ["safflower", "karale", "करडई"],
+    "castor":      ["castor", "erandi", "एरंडी"],
+    "sesame":      ["sesame", "til", "तीळ", "तिळ"],
+    "flower":      ["marigold", "zendu", "झेंडू", "gulab", "गुलाब", "फुलशेती"],
 }
 
+# CROP_KEYWORDS = combined — message_handler.py cha crop-save logic sathi vaparla jato
+CROP_KEYWORDS = {**KB_CROPS, **OTHER_CROPS}
+
 def _detect_crops(text: str, farmer_crops: list) -> list:
     """Question madhe specific crop mention kela ka — nahi tar farmer.crops vapar"""
     t = text.lower()
@@ -444,67 +493,88 @@
         return found
     return [c.lower() for c in farmer_crops] if farmer_crops else []
 
-def _get_context(question: str, farmer: dict) -> str:
+_DISEASE_MAP = {
+    "onion": "onion_disease", "tomato": "tomato_disease",
+    "cotton": "cotton_disease", "soybean": "soybean_disease",
+    "grape": "grape_disease", "pomegranate": "pomegranate_disease",
+    "potato": "potato_disease", "wheat": "wheat_disease",
+    "chilli": "chilli_disease", "brinjal": "brinjal_disease",
+    "sugarcane": "sugarcane_disease",
+}
+_FERT_MAP = {
+    "onion": "fertilizer_onion", "tomato": "fertilizer_tomato",
+    "cotton": "fertilizer_cotton", "soybean": "fertilizer_soybean",
+    "grape": "fertilizer_grape", "pomegranate": "fertilizer_pomegranate",
+    "potato": "fertilizer_potato", "wheat": "fertilizer_wheat",
+    "chilli": "fertilizer_chilli", "brinjal": "fertilizer_brinjal",
+    "sugarcane": "fertilizer_sugarcane",
+}
+
+def _get_context(question: str, farmer: dict) -> tuple:
+    """Returns (context_str, specific_kb_found: bool, unmapped_crops: list)
+    specific_kb_found=False means — active_crops OLakhle gele, pan KNOWLEDGE dict madhe
+    tyanchi specific entry nahi (उदा. आंबा, ज्वारी) → asha veli web search FORCE karaycha
+    ani LLM la स्वतःच्या ज्ञानाने उत्तर द्यायला सांगायचं (deflect न करता)."""
     q = question.lower()
     farmer_crops = farmer.get("crops", [])
     active_crops = _detect_crops(question, farmer_crops)
     parts = []
-
-    disease_map = {
-        "onion": "onion_disease", "tomato": "tomato_disease",
-        "cotton": "cotton_disease", "soybean": "soybean_disease",
-        "grape": "grape_disease", "pomegranate": "pomegranate_disease",
-        "potato": "potato_disease", "wheat": "wheat_disease",
-        "chilli": "chilli_disease", "brinjal": "brinjal_disease",
-        "sugarcane": "sugarcane_disease",
-    }
-    fert_map = {
-        "onion": "fertilizer_onion", "tomato": "fertilizer_tomato",
-        "cotton": "fertilizer_cotton", "soybean": "fertilizer_soybean",
-        "grape": "fertilizer_grape", "pomegranate": "fertilizer_pomegranate",
-        "potato": "fertilizer_potato", "wheat": "fertilizer_wheat",
-        "chilli": "fertilizer_chilli", "brinjal": "fertilizer_brinjal",
-        "sugarcane": "fertilizer_sugarcane",
-    }
+    specific_found = False
+    unmapped = []
 
     if any(w in q for w in DISEASE_WORDS):
         if len(active_crops) > 1:
-            # Multiple pikancha naव ekach veles aalay — pratyek pikache context vegle label karun de
             for crop in active_crops:
-                key = disease_map.get(crop)
+                key = _DISEASE_MAP.get(crop)
                 if key and KNOWLEDGE.get(key):
                     parts.append(f"--- {crop.upper()} साठी माहिती ---\n{KNOWLEDGE[key]}")
+                    specific_found = True
+                elif crop in OTHER_CROPS:
+                    unmapped.append(crop)
         else:
             for crop in active_crops:
-                key = disease_map.get(crop)
+                key = _DISEASE_MAP.get(crop)
                 if key and KNOWLEDGE.get(key):
                     parts.append(KNOWLEDGE[key])
+                    specific_found = True
+                elif crop in OTHER_CROPS:
+                    unmapped.append(crop)
         parts.append(KNOWLEDGE["pest_control"])
 
     if any(w in q for w in FERTILIZER_WORDS):
         for crop in active_crops:
-            key = fert_map.get(crop)
+            key = _FERT_MAP.get(crop)
             if key and KNOWLEDGE.get(key):
                 parts.append(KNOWLEDGE[key])
+                specific_found = True
+            elif crop in OTHER_CROPS and crop not in unmapped:
+                unmapped.append(crop)
 
     if any(w in q for w in SEASON_WORDS):
         parts.append(KNOWLEDGE["seasonal_calendar"])
+        specific_found = True
 
     if any(w in q for w in WATER_WORDS):
         parts.append(KNOWLEDGE["irrigation"])
+        specific_found = True
 
     if any(w in q for w in SCHEME_WORDS):
         parts.append(KNOWLEDGE["government_schemes"])
+        specific_found = True
 
-    # Default fallback — kahi match nahi zala tar farmer chya crops chi info de
+    # Default fallback — kahi intent match nahi zala tar farmer chya crops chi info de
     if not parts:
         for crop in active_crops:
-            d_key = disease_map.get(crop)
-            f_key = fert_map.get(crop)
-            if d_key and KNOWLEDGE.get(d_key): parts.append(KNOWLEDGE[d_key])
-            if f_key and KNOWLEDGE.get(f_key): parts.append(KNOWLEDGE[f_key])
+            d_key = _DISEASE_MAP.get(crop)
+            f_key = _FERT_MAP.get(crop)
+            if d_key and KNOWLEDGE.get(d_key):
+                parts.append(KNOWLEDGE[d_key]); specific_found = True
+            if f_key and KNOWLEDGE.get(f_key):
+                parts.append(KNOWLEDGE[f_key]); specific_found = True
+            if crop in OTHER_CROPS and crop not in unmapped:
+                unmapped.append(crop)
 
-    return "\n\n".join(parts)
+    return "\n\n".join(parts), specific_found, unmapped
 
 # ── API Calls ──────────────────────────────────────────────────────────────
 async def _cerebras_call(messages: list, max_tokens: int = 600) -> str:
@@ -573,10 +643,16 @@
         log.error(f"Tavily search failed: {e}")
         return ""
 
-async def _needs_web_search(question: str, context: str) -> bool:
-    """KNOWLEDGE dict madhe answer nasel tarच web search karaycha — quota vachvaycha"""
+async def _needs_web_search(question: str, context: str, specific_found: bool, unmapped_crops: list) -> bool:
+    """KNOWLEDGE dict madhe accurate answer nasel tarच web search karaycha — quota vachvaycha.
+    specific_found=False (crop KB madhe nahi, e.g. आंबा/ज्वारी) किंवा context रिकामा असेल
+    तर FORCE search — nahitar agent generic/चुकीचं उत्तर देईल."""
     if not context or not context.strip():
         return True
+    if not specific_found:
+        return True
+    if unmapped_crops:
+        return True
     q_lower = question.lower()
     if any(w in q_lower for w in _WEB_SEARCH_TRIGGER_WORDS):
         return True
@@ -597,14 +673,16 @@
         crops = ", ".join(farmer_crops) or "सांगितले नाही"
         city = farmer.get("city", "Pune")
         district = farmer.get("district", "Pune")
-        context = _get_context(question, farmer)
+        context, specific_found, unmapped_crops = _get_context(question, farmer)
 
-        # Tavily web search — फक्त KNOWLEDGE dict madhe answer nasel tarच (max 1 call/message)
-        if TAVILY_API_KEY and await _needs_web_search(question, context):
-            tavily_query = _build_tavily_query(question, farmer_crops)
+        # Tavily web search — KNOWLEDGE dict madhe accurate/specific answer nasel tarच
+        needs_search = await _needs_web_search(question, context, specific_found, unmapped_crops)
+        if TAVILY_API_KEY and needs_search:
+            tavily_query = _build_tavily_query(question, farmer_crops or unmapped_crops)
             web_info = await _tavily_search(tavily_query)
             if web_info:
                 context = (context + f"\n\nइंटरनेट माहिती:\n{web_info}").strip()
+                specific_found = True
 
         messages = [{"role": "system", "content": SYSTEM}]
 
@@ -619,6 +697,19 @@
         if context:
             user_content += f"\n\nसंदर्भ माहिती:\n{context}"
         user_content += f"\n\nप्रश्न: {question}"
+
+        # KB/web मध्ये exact match nasel tar — LLM ला स्वतःच्या agronomy ज्ञानाने best-effort
+        # उत्तर द्यायला सांग (deflect करू नकोस), पण accuracy स्पष्ट सांग.
+        if not specific_found:
+            user_content += (
+                "\n\n[सूचना: वरील संदर्भात या प्रश्नाचं exact answer नाही. तरी तुझ्या स्वतःच्या "
+                "कृषी ज्ञानाने प्रामाणिक, practical उत्तर दे — टाळू नकोस किंवा फक्त 'कृषी केंद्राला विचारा' "
+                "असं म्हणून थांबू नकोस. उत्तराच्या शेवटी एका ओळीत 🎯 अचूकता: मध्यम — असं लिही आणि "
+                "जवळच्या कृषी सेवा केंद्र/1800-180-1551 वर खात्री करायला सांग.]"
+            )
+        else:
+            user_content += "\n\n[उत्तराच्या शेवटी एका ओळीत 🎯 अचूकता: उच्च — असं लिही, कारण ही माहिती पडताळलेल्या स्रोतातून आहे.]"
+
         messages.append({"role": "user", "content": user_content})
 
         ans = await _cerebras_call(messages, 350)
