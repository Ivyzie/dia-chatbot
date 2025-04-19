# chat_engine.py
"""
Phase 4: wiring everything end‑to‑end
––––––––––––––––––––––––––––––––––––
• Intent + emotion (Phase 3)
• Category‑filtered retrieval (Phase 2)
• Prompt template loaded from prompts/assistant_prompt.txt
• Local chat‑LLM (Mistral‑7B Instruct Q4_K_M via ctransformers)

Run:  python chat_engine.py
"""

import os
import logging
from pathlib import Path
from textwrap import shorten

from intent_emotion_router import analyse           # (intent, emotion)
from kbretriever import build_retriever             # your Phase 2 code
from tools.llm_loader import load_llm                     # returns ctransformers model
from transformers import AutoTokenizer

# ────────────────────────────────────────────────────────────
# Settings
# ────────────────────────────────────────────────────────────
CLASS_NAME      = os.getenv("WEAV_CLASS", "CarList")   # Weaviate class
CHUNK_MAX_CHARS = 500                                  # truncate per chunk
MAX_NEW_TOKENS  = 250
TEMPERATURE     = 0.7

PROMPT_TEMPLATE = Path("prompts/assistant_prompt.txt").read_text()

MAX_PROMPT_TOKENS = 300

_tok = AutoTokenizer.from_pretrained("HuggingFaceH4/zephyr-7b-beta", legacy=False)

# ────────────────────────────────────────────────────────────
# LLM (instance is cached inside load_llm)
# ────────────────────────────────────────────────────────────
llm = load_llm()

# ────────────────────────────────────────────────────────────
# Helper to build the final prompt
# ────────────────────────────────────────────────────────────
def _count_tokens(text: str) -> int:
    return len(_tok.encode(text))

def build_prompt(user_msg: str, docs, intent: str, emotion: str) -> str:
    # pick top‑3 chunks and truncate each at 300 chars
    context_pieces, token_total = [], 0
    for d in docs[:2]:                       # only first 2
        snippet = shorten(d.page_content.replace("\n", " "), 300)
        needed  = _count_tokens(snippet)
        if token_total + needed > MAX_PROMPT_TOKENS:
            break
        context_pieces.append(snippet)
        token_total += needed

    context_block = "\n\n---\n\n".join(context_pieces)

    return PROMPT_TEMPLATE.format(
        emotion=emotion,
        intent=intent,
        context=context_block,
        user=user_msg,
    )

# ────────────────────────────────────────────────────────────
# Single‑turn chat function
# ────────────────────────────────────────────────────────────
def chat_once(user_msg: str) -> str:
    # 1 Intent & emotion
    intent, emotion = analyse(user_msg)

    # 2 Map intent → category filter
    category = {"TechSupport": "Support",
                "SalesInquiry": "Sales"}.get(intent)

    # 3 Retrieve relevant KB chunks
    retriever = build_retriever(CLASS_NAME, category=category)
    docs      = retriever.invoke(user_msg)

    # 4 Build prompt & generate reply
    prompt = build_prompt(user_msg, docs, intent, emotion)
    reply  = llm(prompt,
                 max_new_tokens=MAX_NEW_TOKENS,
                 temperature=TEMPERATURE,
                 stream=False)      # change to True for token streaming
    return reply

# ────────────────────────────────────────────────────────────
# Simple REPL
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)s  %(message)s")
    print("CarList Assistant (type empty line to exit)")
    while True:
        try:
            user = input("\nUser: ")
        except (EOFError, KeyboardInterrupt):
            break
        if not user.strip():
            break
        answer = chat_once(user)
        print("\nAssistant:", answer.strip())
