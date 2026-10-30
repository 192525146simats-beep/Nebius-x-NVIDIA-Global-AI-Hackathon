import html, json, re, time
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Receipt AI", page_icon="🧾", layout="wide")

ROOT = Path(__file__).parent
RES = ROOT / "results"
PREFIX = "Extract company, date and total from this receipt: "
PROMPT = ("Extract the company name, date and total from this receipt text. Copy the company and date exactly as printed. "
          "Reply with exactly one line in this format: company: <company> | date: <date> | total: <total>\n\nReceipt text:\n")
PAT = re.compile(r"company:\s*(.*?)\s*\|\s*date:\s*(.*?)\s*\|\s*total:\s*(.*)", re.I | re.S)
SAMPLE = ("ACME STORES SDN BHD NO 12 JALAN BUNGA KL DATE: 12/03/2018 "
          "1 x COFFEE 12.90 2 x SANDWICH 33.00 TOTAL RM 45.90")
PAGES = ["🏠 Overview", "🔍 Extract", "📦 Dataset Dashboard", "📊 Model Performance", "📘 Guide"]

CSS = """
<style>
@keyframes fadeUp { from{opacity:0; transform:translateY(18px)} to{opacity:1; transform:none} }
@keyframes shine { to { background-position: 200% center; } }
@keyframes grow { from{width:0} to{width:var(--w)} }
@keyframes track { from{background-position:0 0} to{background-position:-30px 0} }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(56,189,248,.5)} 70%{box-shadow:0 0 0 12px rgba(56,189,248,0)} 100%{box-shadow:0 0 0 0 rgba(56,189,248,0)} }
@keyframes slideIn { from{opacity:0; transform:translateX(-22px)} to{opacity:1; transform:none} }

.brand { padding:6px 0 10px; }
.brand .t { font-size:1.6rem; font-weight:800;
  background:linear-gradient(90deg,#38bdf8,#76b900,#38bdf8); background-size:200% auto;
  -webkit-background-clip:text; background-clip:text; color:transparent; animation:shine 4s linear infinite; }
.brand .s { font-size:.7rem; letter-spacing:.16em; opacity:.6; text-transform:uppercase; }

.hero { background:linear-gradient(135deg,#0f172a,#1e1b4b 55%,#064e3b); border-radius:20px; padding:30px 34px;
  color:#e2e8f0; overflow:hidden; animation:fadeUp .8s ease both; margin-bottom:18px; }
.hero .tag { font-family:ui-monospace,Menlo,monospace; letter-spacing:.14em; font-size:.72rem; color:#fbbf24; }
.hero h1 { color:#fff; margin:8px 0 6px; font-size:2.3rem; line-height:1.15; }
.hero p { color:#cbd5e1; margin:0; max-width:680px; }
.hero .bar { height:10px; margin-top:20px; border-radius:99px; opacity:.85;
  background:repeating-linear-gradient(90deg,#76b900 0 18px,transparent 18px 30px); animation:track 1s linear infinite; }

.ptitle { font-size:1.9rem; font-weight:800; margin:4px 0 0; animation:fadeUp .6s ease both; }
.psub { opacity:.65; margin:0 0 16px; }

.kpi { background:rgba(128,128,128,.10); border:1px solid rgba(128,128,128,.25); border-top:4px solid #38bdf8;
  border-radius:14px; padding:14px 16px; animation:fadeUp .7s ease both; transition:transform .2s; height:100%; }
.kpi:hover { transform:translateY(-4px); }
.kpi .kl { font-family:ui-monospace,Menlo,monospace; font-size:.7rem; letter-spacing:.1em; text-transform:uppercase; opacity:.7; }
.kpi .kv { font-size:2.1rem; font-weight:800; margin:2px 0; }
.kpi .ks { font-size:.8rem; opacity:.65; }

.step { background:rgba(128,128,128,.08); border:1px solid rgba(128,128,128,.25); border-radius:14px; padding:14px 16px;
  animation:fadeUp .8s ease both; transition:transform .2s, border-color .2s; height:100%; }
.step:hover { transform:translateY(-5px); border-color:#38bdf8; }
.step .n { font-size:1.6rem; }
.step b { display:block; margin:4px 0; }
.step span { font-size:.88rem; opacity:.7; }

.engine { border-radius:14px; padding:6px 14px; font-weight:700; display:inline-block; margin-bottom:8px; }
.engine.ft { background:rgba(118,185,0,.18); border:1px solid #76b900; }
.engine.nb { background:rgba(56,189,248,.18); border:1px solid #38bdf8; animation:pulse 2.4s infinite; }

.fcard { border:1px solid rgba(128,128,128,.35); border-radius:12px; padding:10px 14px; margin:8px 0;
  background:rgba(128,128,128,.08); animation:slideIn .6s ease both; transition:transform .2s, border-color .2s; }
.fcard:hover { transform:translateY(-3px); border-color:#38bdf8; }
.fcard small { opacity:.65; text-transform:uppercase; letter-spacing:.06em; }
.fcard div { font-size:1.12rem; font-weight:600; word-break:break-word; }
.stat { font-size:.9rem; opacity:.85; }

.barrow { margin:10px 0; animation:fadeUp .7s ease both; }
.barlabel { display:flex; justify-content:space-between; font-size:.9rem; margin-bottom:4px; }
.bartrack { background:rgba(128,128,128,.22); border-radius:999px; height:14px; overflow:hidden; }
.barfill { height:100%; border-radius:999px; width:var(--w); animation:grow 1.4s cubic-bezier(.2,.8,.2,1) both; }
.barfill.ft { background:linear-gradient(90deg,#4d7c0f,#76b900); }
.barfill.nb { background:linear-gradient(90deg,#0284c7,#38bdf8); }

.stButton > button, .stDownloadButton > button { transition: transform .2s; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px) scale(1.03); }
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def parse(s):
    m = PAT.findall(s or "")
    if not m:
        return {"company": "", "date": "", "total": ""}
    c, d, t = m[-1]
    t = t.strip().splitlines()[0] if t.strip() else ""
    return {"company": c.strip(), "date": d.strip(), "total": t.strip()}


def norm_text(s):
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def norm_total(s):
    m = re.search(r"\d[\d,]*\.?\d*", str(s))
    if not m:
        return ""
    try:
        return f"{float(m.group(0).replace(',', '')):.2f}"
    except Exception:
        return ""


def val(x):
    return x if x else "—"


def fmt_pct(v):
    return "—" if v is None else f"{float(v) * 100:.1f}%"


def load_json(name):
    for p in (RES / name, ROOT / name):
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                return None
    return None


@st.cache_data(show_spinner=False)
def load_predictions():
    for p in (RES / "predictions.csv", ROOT / "predictions.csv"):
        if p.exists():
            return pd.read_csv(p, dtype=str).fillna("")
    return None


def get_latency(d):
    if not d:
        return None
    for k, v in d.items():
        if k.startswith("avg_latency") and isinstance(v, (int, float)):
            return v
    return None


def score_engine(df, col):
    rows = {"company": [], "date": [], "total": []}
    for _, r in df.iterrows():
        p = parse(r[col])
        rows["company"].append(norm_text(p["company"]) == norm_text(r["gold_company"]))
        rows["date"].append(norm_text(p["date"]) == norm_text(r["gold_date"]))
        gt = norm_total(r["gold_total"])
        rows["total"].append(norm_total(p["total"]) == gt and gt != "")
    out = pd.DataFrame(rows)
    out["all"] = out[["company", "date", "total"]].all(axis=1)
    return out


def kpi(label, value, sub="", accent="#38bdf8"):
    return (f'<div class="kpi" style="border-top-color:{accent}"><div class="kl">{html.escape(label)}</div>'
            f'<div class="kv">{html.escape(str(value))}</div><div class="ks">{html.escape(sub)}</div></div>')


def head(title, sub):
    st.markdown(f'<div class="ptitle">{html.escape(title)}</div><div class="psub">{html.escape(sub)}</div>',
                unsafe_allow_html=True)


def bar_html(label, frac, cls, delay=0.0):
    frac = max(0.0, min(1.0, float(frac)))
    return (f'<div class="barrow" style="animation-delay:{delay:.2f}s"><div class="barlabel"><span>{html.escape(label)}</span>'
            f'<b>{frac * 100:.1f}%</b></div><div class="bartrack"><div class="barfill {cls}" style="--w:{frac * 100:.1f}%"></div></div></div>')


def fields_html(parsed):
    out = ""
    for i, k in enumerate(("company", "date", "total")):
        out += (f'<div class="fcard" style="animation-delay:{i * 0.18:.2f}s"><small>{k}</small>'
                f'<div>{html.escape(val(parsed.get(k, "")))}</div></div>')
    return out


# ---------- engines ----------
@st.cache_resource(show_spinner=False)
def load_t5():
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    name = st.secrets["HF_MODEL"]
    return AutoTokenizer.from_pretrained(name), AutoModelForSeq2SeqLM.from_pretrained(name).eval(), torch


def run_t5(text):
    tok, m, torch = load_t5()
    t0 = time.time()
    enc = tok(PREFIX + text, max_length=768, truncation=True, return_tensors="pt")
    with torch.no_grad():
        out = m.generate(**enc, max_new_tokens=64, num_beams=1)
    return tok.decode(out[0], skip_special_tokens=True), time.time() - t0


def run_nemotron(text):
    from openai import OpenAI
    c = OpenAI(api_key=st.secrets["NEBIUS_API_KEY"], base_url=st.secrets["NEBIUS_BASE_URL"])
    t0 = time.time()
    r = c.chat.completions.create(model=st.secrets["NEBIUS_MODEL"], temperature=0, max_tokens=200,
                                  messages=[{"role": "user", "content": PROMPT + text}])
    txt = re.sub(r"<think>.*?</think>", "", r.choices[0].message.content or "", flags=re.S)
    return txt, time.time() - t0, r.usage.total_tokens


def ocr(img):
    import pytesseract
    return pytesseract.image_to_string(img)


# ---------- navigation ----------
if "page" not in st.session_state:
    st.session_state["page"] = PAGES[0]


def go(p):
    st.session_state["page"] = p


with st.sidebar:
    st.markdown('<div class="brand"><div class="t">🧾 Receipt AI</div>'
                '<div class="s">Receipt field extraction</div></div>', unsafe_allow_html=True)
    st.radio("Navigate", PAGES, key="page", label_visibility="collapsed")
    st.divider()
    price = st.number_input("Nebius price per 1M tokens (USD). Copy it from the Nebius pricing page.",
                            0.0, 100.0, 0.0, 0.01)
    st.caption("Cost is only an estimate: tokens × the price you enter.")
    st.caption("Research prototype. Always check extracted values against the receipt.")


# ---------- pages ----------
def page_overview():
    st.markdown(
        '<div class="hero"><div class="tag">RESEARCH PROTOTYPE · FLAN-T5 · NVIDIA NEMOTRON · NEBIUS</div>'
        '<h1>Pull the company, date and total out of any receipt</h1>'
        '<p>A small fine-tuned model competes with NVIDIA Nemotron on Nebius Token Factory. '
        'Try it on your own receipts, then explore how both did on a held-out test set.</p>'
        '<div class="bar"></div></div>', unsafe_allow_html=True)

    b1, b2, _ = st.columns([1, 1.3, 3])
    b1.button("🔍 Try the extractor", type="primary", on_click=go, args=(PAGES[1],))
    b2.button("📦 Open dataset dashboard", on_click=go, args=(PAGES[2],))

    ft, nb = load_json("finetuned_metrics.json"), load_json("nemotron_zero_shot.json")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Held-out receipts", (ft or {}).get("n", "—"), "never seen in training"), unsafe_allow_html=True)
    c2.markdown(kpi("Fine-tuned · all 3 fields", fmt_pct((ft or {}).get("all_fields")), "exact match", "#76b900"),
                unsafe_allow_html=True)
    c3.markdown(kpi("Nemotron · all 3 fields", fmt_pct((nb or {}).get("all_fields")),
                    "zero-shot, exact match" if nb else "baseline not run yet"), unsafe_allow_html=True)
    lat = get_latency(ft)
    c4.markdown(kpi("Fine-tuned latency", "—" if lat is None else f"{lat:.2f}s", "per receipt (batched)", "#fbbf24"),
                unsafe_allow_html=True)

    st.markdown("### How it works")
    s = st.columns(4)
    steps = [("📷", "1 · Input", "Upload a receipt photo or paste its text."),
             ("🔤", "2 · OCR", "Tesseract turns a photo into text."),
             ("🤖", "3 · Two engines", "Fine-tuned flan-t5-small and Nemotron on Nebius read the same text."),
             ("⚖️", "4 · Compare", "Fields, latency and estimated cost, side by side.")]
    for col, (ic, t, d) in zip(s, steps):
        col.markdown(f'<div class="step"><div class="n">{ic}</div><b>{t}</b><span>{d}</span></div>',
                     unsafe_allow_html=True)


def page_extract():
    head("🔍 Extract", "Compare both engines on one receipt")
    up = st.file_uploader("Receipt photo", type=["png", "jpg", "jpeg"])
    st.text_area("...or paste receipt text", height=150, key="txt")
    b1, b2, _ = st.columns([1, 1.4, 4])
    go_btn = b1.button("✨ Extract", type="primary")
    b2.button("Use illustrative sample", on_click=lambda: st.session_state.update(txt=SAMPLE))
    if not go_btn:
        return
    txt = st.session_state.get("txt", "")
    if up is not None:
        try:
            from PIL import Image
            with st.spinner("Reading the photo with Tesseract OCR..."):
                txt = ocr(Image.open(up))
            with st.expander("OCR text"):
                st.text(txt)
        except Exception as e:
            st.error(f"OCR failed: {type(e).__name__}: {e}")
            return
    txt = " ".join((txt or "").split())
    if not txt:
        st.warning("Upload a receipt photo or paste some text first.")
        return
    ok_any = False
    a, b = st.columns(2)
    with a:
        st.markdown('<span class="engine ft">🎯 Fine-tuned flan-t5-small</span>', unsafe_allow_html=True)
        try:
            with st.spinner("Fine-tuned model is thinking... (the first run loads the model)"):
                o, lat = run_t5(txt)
            st.markdown(fields_html(parse(o)), unsafe_allow_html=True)
            st.markdown(f'<div class="stat">⏱ {lat:.2f}s on CPU · 💵 no per-call fee</div>', unsafe_allow_html=True)
            ok_any = True
        except Exception as e:
            st.error(f"{type(e).__name__}: {e}")
    with b:
        st.markdown('<span class="engine nb">⚡ NVIDIA Nemotron on Nebius</span>', unsafe_allow_html=True)
        try:
            with st.spinner("Calling Nemotron on Nebius Token Factory..."):
                o, lat, tk = run_nemotron(txt)
            st.markdown(fields_html(parse(o)), unsafe_allow_html=True)
            st.markdown(f'<div class="stat">⏱ {lat:.2f}s · 🔢 {tk} tokens · 💵 est. ${tk * price / 1e6:.6f}</div>',
                        unsafe_allow_html=True)
            ok_any = True
        except Exception as e:
            st.error(f"{type(e).__name__}: {e}")
    if ok_any:
        st.balloons()
        st.toast("Extraction complete!", icon="✅")


def page_dataset():
    head("📦 Dataset Dashboard", "Every held-out receipt: gold answer vs each model's prediction")
    df = load_predictions()
    if df is None:
        st.warning("results/predictions.csv was not found. Create it in the Kaggle notebook, "
                   "upload it to the repo's results/ folder, then reload (steps are on the Guide page).")
        return
    engines = [("Fine-tuned flan-t5-small", "ft_raw", "ft", "#76b900")]
    if "nemotron_raw" in df.columns:
        engines.append(("NVIDIA Nemotron (zero-shot)", "nemotron_raw", "nb", "#38bdf8"))
    scores = {name: score_engine(df, col) for name, col, _, _ in engines}

    cols = st.columns(len(engines) + 1)
    cols[0].markdown(kpi("Receipts", len(df), "held-out test set"), unsafe_allow_html=True)
    for c, (name, _, _, color) in zip(cols[1:], engines):
        c.markdown(kpi(name, fmt_pct(scores[name]["all"].mean()), "all 3 fields exact", color), unsafe_allow_html=True)
    if len(engines) == 1:
        st.info("Only the fine-tuned model is in this file so far. The Nemotron column appears once the baseline has been run.")

    st.markdown("#### Accuracy by field")
    chart = pd.DataFrame({name: [s["company"].mean(), s["date"].mean(), s["total"].mean(), s["all"].mean()]
                          for name, s in scores.items()}, index=["Company", "Date", "Total", "All 3"])
    st.bar_chart(chart)

    st.markdown("#### Browse the receipts")
    f1, f2, f3 = st.columns(3)
    eng_name = f1.selectbox("Engine", [e[0] for e in engines])
    show = f2.selectbox("Show", ["All receipts", "Any field wrong", "Company wrong", "Date wrong", "Total wrong", "All correct"])
    q = f3.text_input("Search receipt ID")
    col = {e[0]: e[1] for e in engines}[eng_name]
    sc = scores[eng_name]
    preds = [parse(x) for x in df[col]]
    tick = {True: "✅", False: "❌"}
    table = pd.DataFrame({
        "ID": df["id"],
        "Company (gold)": df["gold_company"], "Company (pred)": [p["company"] for p in preds], "C": sc["company"].map(tick),
        "Date (gold)": df["gold_date"], "Date (pred)": [p["date"] for p in preds], "D": sc["date"].map(tick),
        "Total (gold)": df["gold_total"], "Total (pred)": [p["total"] for p in preds], "T": sc["total"].map(tick),
    })
    mask = pd.Series(True, index=df.index)
    if show == "Any field wrong":
        mask = ~sc["all"]
    elif show == "Company wrong":
        mask = ~sc["company"]
    elif show == "Date wrong":
        mask = ~sc["date"]
    elif show == "Total wrong":
        mask = ~sc["total"]
    elif show == "All correct":
        mask = sc["all"]
    if q:
        mask = mask & df["id"].str.contains(q, case=False, na=False)
    shown = table[mask]
    st.caption(f"{len(shown)} of {len(df)} receipts shown")
    st.dataframe(shown, hide_index=True)
    st.download_button("⬇️ Download this table (CSV)", shown.to_csv(index=False).encode("utf-8"),
                       file_name="receipt_ai_results.csv", mime="text/csv")

    ids = list(df.loc[mask, "id"])
    if ids:
        st.markdown("#### Inspect one receipt")
        pick = st.selectbox("Receipt", ids)
        r = df[df["id"] == pick].iloc[0]
        with st.expander("Receipt text from the dataset (first 600 characters)", expanded=True):
            st.text(r["text"])
        g, p = st.columns(2)
        with g:
            st.markdown('<span class="engine ft">Gold (correct) answer</span>', unsafe_allow_html=True)
            st.markdown(fields_html({"company": r["gold_company"], "date": r["gold_date"], "total": r["gold_total"]}),
                        unsafe_allow_html=True)
        with p:
            st.markdown(f'<span class="engine nb">{html.escape(eng_name)}</span>', unsafe_allow_html=True)
            st.markdown(fields_html(parse(r[col])), unsafe_allow_html=True)
    st.caption("Exact match: company and date must match after whitespace/case normalisation; "
               "total must match numerically (two decimals).")


def page_performance():
    head("📊 Model Performance", "Same metric, same held-out receipts")
    ft, nb = load_json("finetuned_metrics.json"), load_json("nemotron_zero_shot.json")
    if ft is None and nb is None:
        st.warning("No metrics files found. Add results/finetuned_metrics.json and results/nemotron_zero_shot.json.")
    c1, c2 = st.columns(2)
    for col, data, cls, title in [(c1, ft, "ft", "🎯 Fine-tuned flan-t5-small"), (c2, nb, "nb", "⚡ NVIDIA Nemotron zero-shot")]:
        with col:
            st.markdown(f'<span class="engine {cls}">{title}</span>', unsafe_allow_html=True)
            if data is None:
                st.info("Results file not found yet.")
                continue
            rows = ""
            for i, (k, lab) in enumerate([("company", "Company"), ("date", "Date"), ("total", "Total"), ("all_fields", "All 3 fields")]):
                rows += bar_html(lab, data.get(k, 0), cls, i * 0.15)
            st.markdown(rows, unsafe_allow_html=True)
            lat = get_latency(data)
            extra = f" · latency {lat:.2f}s" if lat is not None else ""
            if "avg_total_tokens" in data:
                extra += f" · {data['avg_total_tokens']} tokens/receipt"
            st.caption(f"Model: {data.get('model', '?')} · receipts scored: {data.get('n', '?')}{extra}")
            with st.expander("Raw JSON"):
                st.json(data)
    st.markdown("#### Read these numbers carefully")
    st.markdown(
        "- The fine-tuned model was trained on receipts from the same dataset, while Nemotron is zero-shot, so this is not a like-for-like model comparison.\n"
        "- Exact match is strict: a single character difference counts as wrong.\n"
        "- Photos go through Tesseract OCR, which is noisier than the dataset's text, so expect lower accuracy on phone photos.\n"
        "- Latency for the fine-tuned model was measured on a GPU in batches. The live app runs it on a CPU.")


def page_guide():
    head("📘 Guide", "How to use the app and how the dashboard data is made")
    st.markdown(
        "**Extract** – upload a receipt photo or paste text, then press Extract. Both engines answer side by side.\n\n"
        "**Dataset Dashboard** – reads `results/predictions.csv`, one row per held-out receipt.\n\n"
        "**Model Performance** – reads `results/finetuned_metrics.json` and `results/nemotron_zero_shot.json`.")
    st.markdown("#### Make the dashboard file (Kaggle)")
    st.code('import pandas as pd\n'
            'rows = [{"id": d["id"], "text": d["text"][:600], "gold_company": d["company"],\n'
            '         "gold_date": d["date"], "gold_total": d["total"], "ft_raw": p}\n'
            '        for d, p in zip(test, preds)]\n'
            'df = pd.DataFrame(rows)\n'
            'try:\n'
            '    df["nemotron_raw"] = [r[0] for r in res]\n'
            'except NameError:\n'
            '    pass\n'
            'df.to_csv("results/predictions.csv", index=False)', language="python")
    st.markdown("Download it from the notebook's Output panel and upload it to the repo's `results/` folder on GitHub.")
    st.markdown("#### Limitations")
    st.markdown("- Prototype only; verify every extracted value against the original receipt.\n"
                "- Trained on SROIE-style receipts, so unusual layouts and languages may fail.")


{"🏠 Overview": page_overview, "🔍 Extract": page_extract, "📦 Dataset Dashboard": page_dataset,
 "📊 Model Performance": page_performance, "📘 Guide": page_guide}[st.session_state["page"]]()
