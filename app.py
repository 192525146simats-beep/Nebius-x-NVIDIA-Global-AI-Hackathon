import html, json, re, time
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Receipt AI", page_icon="🧾", layout="wide")

PREFIX = "Extract company, date and total from this receipt: "
PROMPT = ("Extract the company name, date and total from this receipt text. Copy the company and date exactly as printed. "
          "Reply with exactly one line in this format: company: <company> | date: <date> | total: <total>\n\nReceipt text:\n")
PAT = re.compile(r"company:\s*(.*?)\s*\|\s*date:\s*(.*?)\s*\|\s*total:\s*(.*)", re.I | re.S)

CSS = """
<style>
@keyframes bgmove { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes shine { to { background-position: 200% center; } }
@keyframes fadeUp { from{opacity:0; transform:translateY(22px)} to{opacity:1; transform:none} }
@keyframes slideIn { from{opacity:0; transform:translateX(-26px)} to{opacity:1; transform:none} }
@keyframes grow { from{width:0} to{width:var(--w)} }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(56,189,248,.55)} 70%{box-shadow:0 0 0 12px rgba(56,189,248,0)} 100%{box-shadow:0 0 0 0 rgba(56,189,248,0)} }
@keyframes floaty { 0%,100%{transform:translateY(0) rotate(-4deg)} 50%{transform:translateY(-8px) rotate(4deg)} }

.hero { text-align:center; padding:22px 10px 8px; animation: fadeUp .9s ease both; }
.hero .icon { display:inline-block; font-size:3rem; animation: floaty 3.2s ease-in-out infinite; }
.hero h1 { margin:0; font-size:2.8rem;
  background: linear-gradient(90deg,#38bdf8,#76b900,#38bdf8); background-size:200% auto;
  -webkit-background-clip:text; background-clip:text; color:transparent; animation: shine 4s linear infinite; }
.hero p { opacity:.75; margin:6px 0 0; }

[data-testid="column"], [data-testid="stColumn"] { animation: fadeUp .8s ease both; }

.engine { border-radius:14px; padding:6px 14px; font-weight:700; display:inline-block; margin-bottom:8px; }
.engine.ft { background:rgba(118,185,0,.18); border:1px solid #76b900; }
.engine.nb { background:rgba(56,189,248,.18); border:1px solid #38bdf8; animation: pulse 2.4s infinite; }

.fcard { border:1px solid rgba(128,128,128,.35); border-radius:12px; padding:10px 14px; margin:8px 0;
  background:rgba(128,128,128,.08); animation: slideIn .6s ease both; transition: transform .2s, border-color .2s; }
.fcard:hover { transform: translateY(-3px); border-color:#38bdf8; }
.fcard small { opacity:.65; text-transform:uppercase; letter-spacing:.06em; }
.fcard div { font-size:1.15rem; font-weight:600; word-break:break-word; }

.stat { font-size:.9rem; opacity:.85; animation: fadeUp .8s .5s ease both; }

.barrow { margin:10px 0; animation: fadeUp .7s ease both; }
.barlabel { display:flex; justify-content:space-between; font-size:.9rem; margin-bottom:4px; }
.bartrack { background:rgba(128,128,128,.22); border-radius:999px; height:14px; overflow:hidden; }
.barfill { height:100%; border-radius:999px; width:var(--w); animation: grow 1.4s cubic-bezier(.2,.8,.2,1) both; }
.barfill.ft { background:linear-gradient(90deg,#4d7c0f,#76b900); }
.barfill.nb { background:linear-gradient(90deg,#0284c7,#38bdf8); }

.stButton > button { transition: transform .2s, box-shadow .2s; }
.stButton > button:hover { transform: translateY(-2px) scale(1.03); }

@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown(
    '<div class="hero"><span class="icon">🧾</span><h1>Receipt AI</h1>'
    '<p>Fine-tuned flan-t5-small vs NVIDIA Nemotron (zero-shot) on Nebius Token Factory</p></div>',
    unsafe_allow_html=True,
)


def parse(s):
    m = PAT.findall(s or "")
    if not m:
        return {"company": "?", "date": "?", "total": "?"}
    c, d, t = m[-1]
    return {"company": c.strip(), "date": d.strip(), "total": t.strip().splitlines()[0]}


def fields_html(parsed):
    out = ""
    for i, k in enumerate(("company", "date", "total")):
        out += (f'<div class="fcard" style="animation-delay:{i * 0.18:.2f}s"><small>{k}</small>'
                f'<div>{html.escape(str(parsed.get(k, "?")))}</div></div>')
    return out


def bar_html(label, frac, cls, delay):
    frac = max(0.0, min(1.0, float(frac)))
    return (f'<div class="barrow" style="animation-delay:{delay:.2f}s"><div class="barlabel"><span>{html.escape(label)}</span>'
            f'<b>{frac * 100:.1f}%</b></div><div class="bartrack"><div class="barfill {cls}" style="--w:{frac * 100:.1f}%"></div></div></div>')


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
        out = m.generate(**enc, max_new_tokens=64, num_beams=2)
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


st.sidebar.markdown("### ⚙️ Settings")
price = st.sidebar.number_input("Nebius price per 1M tokens (USD), copy it from the Nebius pricing page",
                                0.0, 100.0, 0.0, 0.01)
st.sidebar.caption("Cost is only an estimate: tokens x the price you enter.")

tab1, tab2 = st.tabs(["🔍 Try it", "📊 Results"])

with tab1:
    up = st.file_uploader("Receipt photo", type=["png", "jpg", "jpeg"])
    txt = st.text_area("...or paste receipt text", height=160)
    if st.button("✨ Extract", type="primary"):
        if up is not None:
            from PIL import Image
            with st.spinner("Reading the photo with Tesseract OCR..."):
                txt = ocr(Image.open(up))
            with st.expander("OCR text"):
                st.text(txt)
        txt = " ".join((txt or "").split())
        if not txt:
            st.warning("Upload a receipt photo or paste some text first.")
        else:
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

with tab2:
    base = Path(__file__).parent / "results"

    def load(name):
        p = base / name
        return json.loads(p.read_text()) if p.exists() else None

    ft, nb = load("finetuned_metrics.json"), load("nemotron_zero_shot.json")
    if ft is None and nb is None:
        st.warning("No results files found yet. Add results/finetuned_metrics.json and results/nemotron_zero_shot.json.")
    c1, c2 = st.columns(2)
    for col, data, cls, title in [(c1, ft, "ft", "🎯 Fine-tuned flan-t5-small"), (c2, nb, "nb", "⚡ Nemotron zero-shot")]:
        with col:
            st.markdown(f'<span class="engine {cls}">{title}</span>', unsafe_allow_html=True)
            if data is None:
                st.info("Results file not found yet.")
                continue
            rows = ""
            for i, (k, lab) in enumerate([("company", "Company"), ("date", "Date"), ("total", "Total"), ("all_fields", "All 3 fields")]):
                rows += bar_html(lab, data.get(k, 0), cls, i * 0.15)
            st.markdown(rows, unsafe_allow_html=True)
            st.caption(f"Model: {data.get('model', '?')} · receipts scored: {data.get('n', '?')} (exact-match)")
            with st.expander("Raw JSON"):
                st.json(data)
    st.caption("Both engines were scored with the same exact-match metric on the same held-out receipts.")
