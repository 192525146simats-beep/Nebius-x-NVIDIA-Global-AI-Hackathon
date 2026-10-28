import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

MODEL_PATH = MODEL_DIR / "efficientnet_b0.pt"
ANOMALY_PATH = MODEL_DIR / "anomaly_stats.npz"
GUIDELINE_DIR = ROOT / "docs"

IMG_SIZE = 224

# Nebius settings. Check the exact base URL and model IDs in your Nebius console.
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/")
