#!/usr/bin/env python3
"""
KrishiMitra — golden-set तपासणी (accuracy मोजण्यासाठी)

वापर (project च्या मुख्य folder मधून, .env/Render env मध्ये API keys असताना):

    python eval/run_eval.py run                  # सगळे प्रश्न चालवून eval/report.md बनवतो
    python eval/run_eval.py run --limit 5        # फक्त पहिले 5 (quota वाचवण्यासाठी)
    python eval/run_eval.py run --mock           # API न वापरता, script चीच चाचणी
    python eval/run_eval.py export --rating down # 👎 मिळालेली उत्तरं → eval/candidates.json
    python eval/run_eval.py export --recent 40   # अलीकडचे खरे प्रश्न → eval/candidates.json

स्वयंचलित तपासण्या (ही फक्त regression पकडते — उत्तर खरंच बरोबर आहे का हे तज्ज्ञाने report.md वाचूनच ठरवा):
  1. उत्तर मुख्यतः मराठीत आहे का           (शेतकरी मराठीत वाचतात)
  2. उत्तर लहान आहे का                      (default 140 शब्द)
  3. must_include   — अपेक्षित औषध/शब्द (गटातील कोणताही एक चालेल)
  4. must_not_include — चुकीचं पीक/शब्द नसावा
  5. dose           — "forbidden": औषधाचा dose नसावा, "allowed": चालेल, "any": तपासू नको
  6. clarify        — पीक माहीत नसल्यास आधी प्रश्न विचारला पाहिजे
"""
import argparse, asyncio, json, os, re, sys, time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = re.compile(r"[\u0900-\u097F]")
LAT = re.compile(r"[A-Za-z]")


def marathi_ratio(text: str) -> float:
    d, l = len(DEV.findall(text)), len(LAT.findall(text))
    return d / (d + l) if (d + l) else 0.0


def has_dose(text: str) -> bool:
    from app.services.ai_service import _DOSE_UNIT_RE, _DOSE_CTX_RE
    return any(_DOSE_UNIT_RE.search(l) and _DOSE_CTX_RE.search(l) for l in text.split("\n"))


def check(item: dict, ans: str) -> list:
    """अपयशाची कारणं (रिकामी यादी = पास)"""
    fails, low = [], ans.lower()
    if marathi_ratio(ans) < 0.5:
        fails.append(f"मराठी कमी ({marathi_ratio(ans):.0%})")
    mw = item.get("max_words", 140)
    if len(ans.split()) > mw:
        fails.append(f"खूप मोठं ({len(ans.split())} शब्द > {mw})")
    for group in item.get("must_include", []):
        if not any(a.lower() in low for a in group):
            fails.append(f"अपेक्षित शब्द नाही: {' / '.join(group)}")
    for bad in item.get("must_not_include", []):
        if bad.lower() in low:
            fails.append(f"नसावा असा शब्द आला: {bad}")
    if item.get("dose") == "forbidden" and has_dose(ans):
        fails.append("dose दिला (या पिकासाठी नको होता)")
    if item.get("clarify"):
        if not ("?" in ans or "कोणत्या" in ans or "कोणते" in ans or "कोणता" in ans):
            fails.append("पीक विचारलं नाही (clarify अपेक्षित)")
    return fails


async def run(args):
    items = json.load(open(args.questions, encoding="utf-8"))
    if args.limit:
        items = items[: args.limit]

    if args.mock:
        async def fa(q, farmer, history):
            return "🔍 समस्या: रोग\n✅ उपाय: कृषी सेवा केंद्रात विचारा.\n🎯 अचूकता: मध्यम\nपीक कोणतं आहे?"
    else:
        if not os.getenv("GEMINI_API_KEY") and not os.getenv("GROQ_API_KEY"):
            sys.exit("❌ GEMINI_API_KEY / GROQ_API_KEY सापडली नाही — .env भरा किंवा --mock वापरा")
        from app.services.ai_service import farming_answer as fa

    results = []
    for i, it in enumerate(items, 1):
        farmer = {"crops": it.get("crops", []), "city": "पुणे", "district": "पुणे", "state": "महाराष्ट्र"}
        t0 = time.time()
        try:
            ans = await fa(it["q"], farmer, it.get("history", []))
        except Exception as e:
            ans = f"[ERROR] {e}"
        fails = check(it, ans)
        results.append({**it, "answer": ans, "fails": fails, "secs": round(time.time() - t0, 1)})
        print(f"[{i}/{len(items)}] {'✅' if not fails else '❌'} {it['id']}  {'; '.join(fails)}")
        if not args.mock:
            await asyncio.sleep(args.delay)   # free-tier rate limit वाचवण्यासाठी

    passed = sum(1 for r in results if not r["fails"])
    cats = {}
    for r in results:
        c = cats.setdefault(r["category"], [0, 0]); c[1] += 1; c[0] += (not r["fails"])

    out = [f"# KrishiMitra golden-set report — {datetime.now():%d-%m-%Y %H:%M}\n",
           f"**एकूण: {passed}/{len(results)} पास ({passed*100//max(1,len(results))}%)**\n",
           "| गट | पास |\n|---|---|"]
    out += [f"| {c} | {p}/{t} |" for c, (p, t) in cats.items()]
    out.append("\n## ❌ अपयशी प्रश्न\n")
    for r in results:
        if r["fails"]:
            out.append(f"### {r['id']} — {r['q']}\n- कारण: {'; '.join(r['fails'])}\n\n```\n{r['answer']}\n```\n")
    out.append("\n## तज्ज्ञ तपासणी (सर्व उत्तरं — प्रत्येकाला ✔/✘ द्या)\n")
    for r in results:
        out.append(f"**{r['id']}** — {r['q']}\n\n{r['answer']}\n\nतज्ज्ञ: [ ] बरोबर  [ ] चूक — टीप: \n\n---\n")
    open(os.path.join(HERE, "report.md"), "w", encoding="utf-8").write("\n".join(out))
    json.dump(results, open(os.path.join(HERE, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n✅ {passed}/{len(results)} पास → eval/report.md")


def export(args):
    from app.services.database import get_db
    db = get_db()
    if not db:
        sys.exit("❌ SUPABASE_URL / SUPABASE_KEY नाहीत")
    cands = []
    if args.recent:
        rows = (db.table("conversations").select("user_message,bot_response")
                  .order("created_at", desc=True).limit(args.recent * 3).execute().data)
        for r in rows:
            q = (r.get("user_message") or "").strip()
            if q and q not in ("[IMAGE]", "[VOICE]"):
                cands.append({"id": f"recent-{len(cands)+1}", "category": "खरे प्रश्न (तज्ज्ञ तपासा)", "q": q,
                              "crops": [], "must_include": [], "must_not_include": [], "dose": "any",
                              "bot_answer_was": (r.get("bot_response") or "")[:600]})
            if len(cands) >= args.recent:
                break
    else:
        rows = (db.table("feedback").select("user_message,bot_response,rating").eq("rating", args.rating)
                  .order("created_at", desc=True).limit(100).execute().data)
        for r in rows:
            q = (r.get("user_message") or "").strip()
            if q:
                cands.append({"id": f"fb-{args.rating}-{len(cands)+1}", "category": f"feedback {args.rating}", "q": q,
                              "crops": [], "must_include": [], "must_not_include": [], "dose": "any",
                              "bot_answer_was": (r.get("bot_response") or "")[:600]})
    path = os.path.join(HERE, "candidates.json")
    json.dump(cands, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ {len(cands)} प्रश्न → eval/candidates.json\n"
          "   आता तज्ज्ञाकडून बरोबर उत्तर/अपेक्षित औषध भरून घ्या, मग ते golden_questions.json मध्ये टाका.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--questions", default=os.path.join(HERE, "golden_questions.json"))
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--delay", type=float, default=3.0, help="प्रश्नांमधलं अंतर (सेकंद)")
    r.add_argument("--mock", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("--rating", default="down", choices=["down", "up"])
    e.add_argument("--recent", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(run(a)) if a.cmd == "run" else export(a)
