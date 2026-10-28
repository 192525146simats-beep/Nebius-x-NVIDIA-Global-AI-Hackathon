import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from PIL import Image

from edge.patrol_agent import decide
from src.infer import Inspector, models_ready

st.set_page_config(page_title="Live Patrol", page_icon="🤖", layout="wide")
st.title("🤖 Autonomous Patrol (simulation)")
if not models_ready():
    st.error("Train the model first.")
    st.stop()


@st.cache_resource
def get_insp():
    return Inspector()


files = st.file_uploader("Patrol stream (upload track images in order)", type=["jpg", "jpeg", "png"],
                         accept_multiple_files=True)
speed = st.slider("Seconds per frame", 0.1, 2.0, 0.6)
if files and st.button("▶ Start patrol"):
    insp = get_insp()
    c1, c2, c3 = st.columns([2, 2, 1])
    ph_in, ph_cam, ph_state = c1.empty(), c2.empty(), c3.empty()
    strip, table = st.empty(), []
    marks = ["·"] * len(files)
    for i, f in enumerate(sorted(files, key=lambda x: x.name)):
        img = Image.open(f)
        a = insp.analyze(img)
        action, why = decide(a, None)
        marks[i] = "🔴" if action == "STOP" else "🟢"
        ph_in.image(img.convert("RGB").resize((320, 320)), caption=f"Frame {i + 1}: {f.name}")
        ph_cam.image(a["overlay"], caption="Grad-CAM")
        ph_state.metric("State", "🛑 STOP" if action == "STOP" else "🚆 MOVING", f"{i + 1} m · p={a['p_defective']:.2f}")
        strip.markdown("**Track map:** " + "".join(marks))
        if action == "STOP":
            table.append({"odometer_m": i + 1, "frame": f.name, "p_defective": a["p_defective"], "reason": why})
        time.sleep(speed)
    st.success(f"Patrol complete: {len(table)} stop(s) in {len(files)} frames")
    if table:
        st.dataframe(table, use_container_width=True)
