"""Evaluate the stop/continue policy under perturbations. Output: reports/policy_eval.json"""
import json
import sys

import numpy as np
from PIL import Image, ImageFilter

from edge.patrol_agent import decide
from src.config import DATA_DIR, REPORT_DIR
from src.data import find_splits, list_images
from src.infer import Inspector


def perturb(img, cond, rng):
    img = img.convert("RGB")
    if cond == "dark":
        return Image.fromarray((np.asarray(img) * 0.45).astype(np.uint8))
    if cond == "bright":
        return Image.fromarray(np.clip(np.asarray(img) * 1.6, 0, 255).astype(np.uint8))
    if cond == "blur":
        return img.filter(ImageFilter.GaussianBlur(3))
    if cond == "noise":
        a = np.asarray(img).astype(np.float32) + rng.normal(0, 18, np.asarray(img).shape)
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return img


def main(limit=200):
    rng = np.random.default_rng(0)
    insp = Inspector()
    split = find_splits(DATA_DIR).get("test") or find_splits(DATA_DIR)["train"]
    paths = list_images(split)[:limit]
    out = {}
    for cond in ["clean", "dark", "bright", "blur", "noise"]:
        tp = fn = fp = tn = 0
        for p in paths:
            truth_def = "defect" in p.parent.name.lower() and "non" not in p.parent.name.lower()
            a = insp.analyze(perturb(Image.open(p), cond, rng))
            stop = decide(a, None)[0] == "STOP"
            tp += truth_def and stop; fn += truth_def and not stop
            fp += (not truth_def) and stop; tn += (not truth_def) and not stop
        out[cond] = {"missed_defect_rate": round(fn / max(tp + fn, 1), 3),
                     "false_stop_rate": round(fp / max(fp + tn, 1), 3), "n": tp + fn + fp + tn}
        print(cond, out[cond])
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "policy_eval.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
