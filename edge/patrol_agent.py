"""Patrol agent: sense -> detect -> verify -> act -> log.
Simulation:  python -m edge.patrol_agent --source /path/to/images
Webcam:      python -m edge.patrol_agent --source camera
"""
import argparse
import base64
import io
import json
import os
import time
from pathlib import Path

from PIL import Image

from src import llm
from src.config import REPORT_DIR
from src.infer import Inspector
from src.rag import GuidelineIndex

STOP_P, SLOW_P = 0.85, 0.15


class Actuators:
    """Prints in simulation. On a Pi, wires to a buzzer (pin 18) and motor enable (pin 23)."""

    def __init__(self, gpio=False):
        self.gpio = gpio
        if gpio:
            from gpiozero import Buzzer, OutputDevice  # pip install gpiozero
            self.buzzer, self.motor = Buzzer(18), OutputDevice(23)
            self.motor.on()

    def drive(self):
        if self.gpio:
            self.motor.on()

    def stop(self):
        print("   [ACT] MOTOR STOP")
        if self.gpio:
            self.motor.off()

    def alarm(self, secs=1.5):
        print("   [ACT] ALARM")
        if self.gpio:
            self.buzzer.on(); time.sleep(secs); self.buzzer.off()


def cloud_verify(img: Image.Image, a: dict):
    """Ask a vision-capable model on a Nebius Serverless Endpoint. Returns dict or None."""
    model = os.getenv("NEBIUS_MODEL_VLM", "")
    if not (llm.llm_available() and model):
        return None
    buf = io.BytesIO(); img.convert("RGB").save(buf, "JPEG", quality=85)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    prompt = ("This is a railway track image. A classifier gave P(defective)="
              f"{a['p_defective']}. Does the image show a visible track defect that should stop a patrol robot? "
              'Reply with JSON only: {"hazard": true|false, "reason": "<one sentence>"}')
    try:
        r = llm._client().chat.completions.create(
            model=model, max_tokens=300, temperature=0.1,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": uri}}]}])
        return llm._parse(r.choices[0].message.content or "")
    except Exception as e:
        return {"hazard": None, "reason": f"verify failed: {str(e)[:120]}"}


def frames(source: str):
    if source == "camera":
        import cv2
        cap = cv2.VideoCapture(0)
        while cap.isOpened():
            ok, f = cap.read()
            if not ok:
                break
            yield Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)), "camera"
            time.sleep(0.2)
    else:
        exts = {".jpg", ".jpeg", ".png"}
        for p in sorted(Path(source).rglob("*")):
            if p.suffix.lower() in exts:
                yield Image.open(p), p.name


def decide(a: dict, verdict):
    """Policy: returns (action, reason)."""
    if verdict and verdict.get("hazard") is True:
        return "STOP", "cloud verifier confirmed hazard"
    if verdict and verdict.get("hazard") is False and a["p_defective"] < STOP_P:
        return "CONTINUE", "cloud verifier found no hazard"
    if a["p_defective"] >= STOP_P and not a["disagree"]:
        return "STOP", "high-confidence defect"
    if a["uncertain"] or a["disagree"]:
        return "STOP", "uncertain - hold for human review"
    return "CONTINUE", "clear"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--gpio", action="store_true")
    ap.add_argument("--meters-per-frame", type=float, default=1.0)
    ap.add_argument("--no-cloud", action="store_true")
    args = ap.parse_args()

    insp, act = Inspector(), Actuators(args.gpio)
    REPORT_DIR.mkdir(exist_ok=True)
    log = open(REPORT_DIR / "patrol_log.jsonl", "w")
    odo, stats = 0.0, {"frames": 0, "cloud_calls": 0, "stops": 0}

    for img, name in frames(args.source):
        t0 = time.time()
        a = insp.analyze(img)
        odo += args.meters_per_frame
        stats["frames"] += 1
        verdict = None
        if (a["uncertain"] or a["disagree"]) and not args.no_cloud:
            stats["cloud_calls"] += 1
            verdict = cloud_verify(img, a)
        action, why = decide(a, verdict)
        print(f"{odo:7.1f} m | {name[:22]:22} | p={a['p_defective']:.2f} | {action:8} | {why}")
        if action == "STOP":
            stats["stops"] += 1
            act.stop(); act.alarm()
            log.write(json.dumps({"odometer_m": odo, "frame": name, "p_defective": a["p_defective"],
                                  "anomaly_ratio": a["anomaly_ratio"], "reason": why, "verify": verdict,
                                  "latency_s": round(time.time() - t0, 3)}) + "\n")
            log.flush()
            time.sleep(1.0)   # in the demo: operator acknowledges, patrol resumes
            act.drive()
    print("summary:", stats)


if __name__ == "__main__":
    main()
