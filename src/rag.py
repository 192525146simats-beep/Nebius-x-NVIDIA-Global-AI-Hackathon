import re
from collections import Counter
from math import log

from src.config import GUIDELINE_DIR

# Illustrative notes for the demo. Replace with your own documents in docs/*.md or docs/*.txt.
DEFAULT_DOCS = [
    "Cracked rail: stop traffic over the section and request an immediate ultrasonic or visual inspection.",
    "Missing or loose fastener: reduce speed, mark the location and schedule urgent maintenance.",
    "Ballast loss or washout: check track geometry and drainage before allowing normal speed.",
    "Rust or surface wear: log the location and schedule a routine maintenance check.",
    "Uncertain automated result: hold the vehicle and ask a human inspector to confirm.",
    "Vegetation or debris on track: clear obstruction and re-inspect the section.",
]


def _tok(s):
    return re.findall(r"[a-z]+", s.lower())


class GuidelineIndex:
    """Tiny keyword-based retriever. No extra dependencies."""

    def __init__(self):
        self.docs = list(DEFAULT_DOCS)
        if GUIDELINE_DIR.exists():
            for p in sorted(GUIDELINE_DIR.glob("*")):
                if p.suffix.lower() in {".md", ".txt"}:
                    self.docs += [x.strip() for x in p.read_text(errors="ignore").split("\n\n") if x.strip()]
        self.tokens = [Counter(_tok(d)) for d in self.docs]
        df = Counter(w for t in self.tokens for w in t)
        n = len(self.docs)
        self.idf = {w: log((n + 1) / (c + 0.5)) for w, c in df.items()}

    def search(self, query, k=3):
        q = _tok(query)
        scores = [sum(t[w] * self.idf.get(w, 0) for w in q) for t in self.tokens]
        order = sorted(range(len(self.docs)), key=lambda i: -scores[i])[:k]
        return [self.docs[i] for i in order if scores[i] > 0]
