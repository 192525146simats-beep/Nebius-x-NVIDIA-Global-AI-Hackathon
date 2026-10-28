"""Train: python -m src.train --epochs 5
With synthetic data: python -m src.train --data data data/synthetic --epochs 5"""
import argparse
import json
import random

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms

from src.config import ANOMALY_PATH, DATA_DIR, IMG_SIZE, MODEL_DIR, MODEL_PATH, REPORT_DIR
from src.data import RailDataset, find_splits, label_of, list_images
from src.infer import TF, build_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", nargs="+", default=[str(DATA_DIR)])
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    args = ap.parse_args()

    random.seed(0); torch.manual_seed(0)
    train, val = [], []
    for root in args.data:
        sp = find_splits(root)
        if "train" in sp:
            train += list_images(sp["train"])
        v = sp.get("val") or sp.get("test")
        if v:
            val += list_images(v)
    if not train:
        raise SystemExit("No training images found. Check the --data path.")
    if not val:
        random.shuffle(train)
        cut = max(1, len(train) // 5)
        val, train = train[:cut], train[cut:]
    print("train", len(train), "val", len(val))

    aug = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)), transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(0.3, 0.3, 0.2), transforms.RandomRotation(8),
        transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    tl = DataLoader(RailDataset(train, aug), batch_size=args.batch, shuffle=True, num_workers=2)
    vl = DataLoader(RailDataset(val, TF), batch_size=args.batch, num_workers=2)

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = build_model(pretrained=True).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    for ep in range(args.epochs):
        model.train()
        for x, y in tl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad(); loss = loss_fn(model(x), y); loss.backward(); opt.step()
        model.eval(); tp = fp = fn = tn = 0
        with torch.no_grad():
            for x, y in vl:
                pred = model(x.to(dev)).argmax(1).cpu()
                tp += int(((pred == 1) & (y == 1)).sum()); fp += int(((pred == 1) & (y == 0)).sum())
                fn += int(((pred == 0) & (y == 1)).sum()); tn += int(((pred == 0) & (y == 0)).sum())
        acc = (tp + tn) / max(tp + fp + fn + tn, 1)
        print(f"epoch {ep + 1}: val acc {acc:.3f} (tp {tp} fp {fp} fn {fn} tn {tn})")

    MODEL_DIR.mkdir(exist_ok=True); REPORT_DIR.mkdir(exist_ok=True)
    model = model.cpu().eval()
    torch.save(model.state_dict(), MODEL_PATH)

    # Anomaly stats from non-defective training images
    feats = []
    from PIL import Image
    normal = [p for p in train if label_of(p) == 0][:500]
    with torch.no_grad():
        for p in normal:
            f = model.features(TF(Image.open(p).convert("RGB")).unsqueeze(0)).mean((2, 3))[0].numpy()
            feats.append(f)
    if len(feats) >= 10:
        F = np.stack(feats); mean, var = F.mean(0), F.var(0)
        d = np.sqrt(np.mean((F - mean) ** 2 / (var + 1e-6), axis=1))
        np.savez(ANOMALY_PATH, mean=mean, var=var, thr=float(np.percentile(d, 95)))
    (REPORT_DIR / "metrics.json").write_text(json.dumps(
        {"val_accuracy": round(acc, 4), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
         "train_images": len(train), "val_images": len(val)}, indent=2))
    print("saved", MODEL_PATH)


if __name__ == "__main__":
    main()
