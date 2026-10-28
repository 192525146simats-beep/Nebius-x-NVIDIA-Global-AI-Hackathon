"""Generate lighting/weather variants of the training images into data/synthetic/."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from src.config import DATA_DIR, ROOT
from src.data import find_splits, list_images

OUT = ROOT / "data" / "synthetic"


def variants(img, rng):
    yield "dark", ImageEnhance.Brightness(img).enhance(0.45)
    yield "glare", ImageEnhance.Brightness(img).enhance(1.6)
    yield "blur", img.filter(ImageFilter.GaussianBlur(2.5))
    a = np.asarray(img).astype(np.float32)
    h = a.shape[0]
    a[: h // 2] *= 0.6   # shadow across the upper half
    yield "shadow", Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    a = np.asarray(img).astype(np.float32) + rng.normal(0, 15, a.shape)
    yield "noise", Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    rng = np.random.default_rng(1)
    n = 0
    for p in list_images(find_splits(DATA_DIR)["train"]):
        img = Image.open(p).convert("RGB")
        for tag, v in variants(img, rng):
            d = OUT / p.parent.name
            d.mkdir(parents=True, exist_ok=True)
            v.save(d / f"{p.stem}_{tag}.jpg")
            n += 1
    print("wrote", n, "synthetic images to", OUT)


if __name__ == "__main__":
    main()
