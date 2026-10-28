from pathlib import Path

from PIL import Image
from torch.utils.data import Dataset

EXTS = {".jpg", ".jpeg", ".png"}
SPLIT_ALIASES = {"train": "train", "training": "train", "test": "test", "testing": "test",
                 "val": "val", "valid": "val", "validation": "val"}


def list_images(folder):
    folder = Path(folder)
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)


def find_splits(root):
    """Return {'train': Path, 'test': Path, 'val': Path} for whichever exist under root."""
    root = Path(root)
    out = {}
    if not root.exists():
        return out
    for d in sorted(root.rglob("*")):
        if not d.is_dir():
            continue
        if "synthetic" in d.relative_to(root).parts:
            continue
        key = SPLIT_ALIASES.get(d.name.lower())
        if key and key not in out and list_images(d):
            out[key] = d
    if not out and list_images(root):
        out["train"] = root
    return out


def label_of(path):
    """1 = defective, 0 = non-defective, decided from the class folder name."""
    n = Path(path).parent.name.lower().replace("-", " ").replace("_", " ")
    bad_words = ("non", "no ", "not", "good", "normal", "ok")
    return int("defect" in n and not any(w in n for w in bad_words))


class RailDataset(Dataset):
    def __init__(self, paths, transform):
        self.paths, self.transform = list(paths), transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        p = self.paths[i]
        return self.transform(Image.open(p).convert("RGB")), label_of(p)
