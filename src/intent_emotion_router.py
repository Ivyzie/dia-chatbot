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
    "TechSupport": [
        # Website/app functionality
        "website technical issue",
        "app functionality problem",
        "website feature not working",
        "broken website function",
        "site error message",
        # Account/settings
        "account settings problem",
        "user profile issue",
        "notification settings issue",
        "email preferences problem",
        "user account access issue",
        # UI-specific patterns
        "interface element not loading",
        "button not working properly",
        "cannot upload files to website",
        "website display problem",
        "form submission error",
        # Common misclassified queries
        "how do I change settings",
        "cannot access my account information",
        "website configuration help"
    ],
    "SalesInquiry": [
        # Purchase intent
        "buying a car",
        "purchasing vehicle information",
        "car shopping question",
        "vehicle price inquiry",
        "car availability question",
        # Dealership
        "dealership information request",
        "test drive booking",
        "car purchase process",
        # Financial
        "car loan information",
        "vehicle financing question",
        "payment options for cars",
        # Inventory-specific
        "specific car model availability",
        "car with certain features availability",
        "do you have this car in stock",
        # Distinguishing from ProductFAQ
        "car specs for buying decision",
        "features available on models for sale"
    ],
    "ProductFAQ": [
        # Pure information
        "car technical information",
        "vehicle specifications question",
        "how does this car feature work",
        "general car knowledge question",
        # Maintenance
        "car maintenance information",
        "vehicle service requirements",
        "car part information",
        # Comparisons
        "compare different car models",
        "difference between car features",
        # Technical details
        "engine specifications question",
        "car dimensions information",
        "vehicle technical details",
        # Distinguishing from SalesInquiry
        "car spec information not for purchase",
        "general automotive knowledge"
    ]
}

def classify_intent(msg: str) -> str:
    msg_lower = msg.lower()
    
    # Direct classification for very clear patterns
    if any(word in msg_lower for word in ["website", "app", "login", "site"]) and \
       any(word in msg_lower for word in ["error", "broken", "not working", "issue", "problem"]):
        return "TechSupport"
    
    if any(word in msg_lower for word in ["price", "cost", "buy", "purchase"]) and \
       any(word in msg_lower for word in ["car", "vehicle", "honda", "toyota"]):
        return "SalesInquiry"
        
    if any(word in msg_lower for word in ["how", "what is", "explain", "difference"]) and \
       any(word in msg_lower for word in ["feature", "engine", "specification", "consumption"]):
        return "ProductFAQ"
    

    # Strong keyword signals for specific misclassification patterns
    tech_signals = ["can't access", "not working", "error", "broken", "reset", "enable", "disable", 
                  "settings", "upload", "login", "password", "account", "notification"]
    sales_signals = ["buy", "purchase", "price", "financing", "loan", "test drive", "dealership", 
                    "booking", "appointment", "available", "in stock", "down payment"]
    product_signals = ["specification", "feature", "dimension", "compare", "difference", "engine", 
                  "capacity", "size", "work", "mean", "stand for", "better", "fuel", "consumption",
                  "maintenance", "service", "reliability", "worth", "performance", "economy", 
                  "transmission", "lifespan", "typically", "recommended", "airbags", "safety"]
    
    # Check for strong signals in commonly confused queries
    tech_count = sum(1 for word in tech_signals if word in msg_lower)
    sales_count = sum(1 for word in sales_signals if word in msg_lower)
    product_count = sum(1 for word in product_signals if word in msg_lower)
    
    # Regular NLI classification
    nli = _intent_pipe()
    best, score = None, 0.0
    for intent, hyps in LABEL_HYPOTHESES.items():
        for hyp in hyps:
            res   = nli(f"{msg} </s></s> {hyp}")[0]
            ent_d = next((x for x in res if x["label"].lower() == "entailment"), None)
            if ent_d and ent_d["score"] > score:
                best, score = intent, ent_d["score"]
    
     # Handle ambiguous cases with keyword signals
    if best == "ProductFAQ" and score < 0.8:
        if tech_count > 2 and tech_count > product_count:
            return "TechSupport"
        if sales_count > 2 and sales_count > product_count:
            return "SalesInquiry"
    

    if score < 0.30:  # 
        if tech_count >= 2:
            return "TechSupport"
        if sales_count >= 2:  
            return "SalesInquiry"
        if product_count >= 2:  
            return "ProductFAQ"
        return "UnknownIntent"
    
    return best or "UnknownIntent"

def detect_emotion(msg: str) -> str:
    preds = _emotion_pipe()(msg)[0]                  
    return max(preds, key=lambda x: x["score"])["label"]

def analyse(msg: str) -> Tuple[str, str]:
    """Return (intent, emotion)."""
    return classify_intent(msg), detect_emotion(msg)
