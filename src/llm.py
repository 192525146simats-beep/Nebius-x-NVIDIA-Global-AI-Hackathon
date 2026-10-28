import json
import os
import re

from src.config import NEBIUS_BASE_URL


def llm_available():
    return bool(os.getenv("NEBIUS_API_KEY"))


def _client():
    from openai import OpenAI
    return OpenAI(base_url=NEBIUS_BASE_URL, api_key=os.getenv("NEBIUS_API_KEY", ""))


def _parse(text: str):
    """Pull the first JSON object out of a model reply. Returns dict, or {} if none."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def explain(analysis: dict, guidelines: list):
    """Short text report for the main app. Returns None if no key or model is set."""
    model = os.getenv("NEBIUS_MODEL", "")
    if not (llm_available() and model):
        return None
    ctx = "\n".join(f"- {g}" for g in guidelines)
    prompt = (f"A classifier rated this track image P(defective)={analysis['p_defective']}, "
              f"anomaly ratio {analysis['anomaly_ratio']}. Relevant guidance:\n{ctx}\n"
              "Write a 3 sentence inspection note and a recommended action. "
              "State that this is an automated screening result.")
    try:
        r = _client().chat.completions.create(
            model=model, max_tokens=300, temperature=0.2,
            messages=[{"role": "user", "content": prompt}])
        return r.choices[0].message.content
    except Exception as e:
        return f"LLM call failed: {str(e)[:120]}"
