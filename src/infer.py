import numpy as np
import torch
from PIL import Image
from torch import nn
from torchvision import models, transforms

from src.config import ANOMALY_PATH, IMG_SIZE, MODEL_PATH

STOP_P, SLOW_P = 0.85, 0.15

TF = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def build_model(pretrained=False):
    w = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
    m = models.efficientnet_b0(weights=w)
    m.classifier[1] = nn.Linear(m.classifier[1].in_features, 2)
    return m


def models_ready():
    return MODEL_PATH.exists()


def _colorize(c):
    r = np.clip(1.5 - np.abs(4 * c - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * c - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * c - 1), 0, 1)
    return (np.stack([r, g, b], -1) * 255).astype(np.uint8)


class Inspector:
    """Classifier + Grad-CAM + feature-distance anomaly check."""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = build_model()
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval().to(self.device)
        self.stats = None
        if ANOMALY_PATH.exists():
            z = np.load(ANOMALY_PATH)
            self.stats = (z["mean"], z["var"], float(z["thr"]))

    def analyze(self, img: Image.Image) -> dict:
        img = img.convert("RGB")
        x = TF(img).unsqueeze(0).to(self.device).requires_grad_(True)
        store = {}

        def hook(_m, _i, o):
            o.retain_grad()
            store["a"] = o

        h = self.model.features.register_forward_hook(hook)
        with torch.enable_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, 1)[0]
            self.model.zero_grad(set_to_none=True)
            logits[0, 1].backward()
        h.remove()

        a, g = store["a"].detach(), store["a"].grad.detach()
        cam = torch.relu((g.mean((2, 3), keepdim=True) * a).sum(1))[0].cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        cam = np.asarray(Image.fromarray((cam * 255).astype(np.uint8)).resize(img.size, Image.BILINEAR)) / 255.0
        overlay = (0.55 * np.asarray(img) + 0.45 * _colorize(cam)).astype(np.uint8)

        p = float(probs[1])
        ratio = 0.0
        if self.stats is not None:
            mean, var, thr = self.stats
            f = a.mean((2, 3))[0].cpu().numpy()
            d = float(np.sqrt(np.mean((f - mean) ** 2 / (var + 1e-6))))
            ratio = d / (thr + 1e-8)
        uncertain = SLOW_P < p < STOP_P
        disagree = False
        if self.stats is not None:
            disagree = (p < 0.5 and ratio > 1.3) or (p >= 0.5 and ratio < 0.6)
        return {"p_defective": round(p, 4), "anomaly_ratio": round(ratio, 3),
                "uncertain": bool(uncertain), "disagree": bool(disagree),
                "label": "defective" if p >= 0.5 else "non-defective", "overlay": overlay}
