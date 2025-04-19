import functools
from typing import Tuple
from transformers import (
    pipeline, AutoTokenizer, AutoModelForSequenceClassification
)

# ── lazy pipelines ────────────────────────────────────────────────────────
@functools.lru_cache(1)
def _intent_pipe():
    mdl = "facebook/bart-large-mnli"
    return pipeline(
        "text-classification",
        model=AutoModelForSequenceClassification.from_pretrained(mdl),
        tokenizer=AutoTokenizer.from_pretrained(mdl),
        top_k=None,                # modern arg; returns scores
        device=0                  # set 0 for GPU
    )

@functools.lru_cache(1)
def _emotion_pipe():
    return pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        top_k=None,
        device=0                  # set 0 for GPU
    )

# ── intent helper ─────────────────────────────────────────────────────────
LABEL_HYPOTHESES = {
    "TechSupport":  ["tech support request"],
    "SalesInquiry": ["sales inquiry"],
    "ProductFAQ":   ["product FAQ"]
}

def classify_intent(msg: str) -> str:
    nli = _intent_pipe()
    best, score = None, 0.0
    for intent, hyps in LABEL_HYPOTHESES.items():
        for hyp in hyps:
            res   = nli(f"{msg} </s></s> {hyp}")[0]   # list[dict]
            ent_d = next((x for x in res if x["label"].lower() == "entailment"), None)
            if ent_d and ent_d["score"] > score:
                best, score = intent, ent_d["score"]
    return best or "UnknownIntent"

def detect_emotion(msg: str) -> str:
    preds = _emotion_pipe()(msg)[0]                  # first (and only) sample
    return max(preds, key=lambda x: x["score"])["label"]

def analyse(msg: str) -> Tuple[str, str]:
    """Return (intent, emotion)."""
    return classify_intent(msg), detect_emotion(msg)
