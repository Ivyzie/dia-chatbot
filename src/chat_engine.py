# chat_engine.py
"""
Phase 4 runtime core (API‑ready)

• analyse()  → intent & emotion
• build_retriever()  → KB context
• load_llm() → Zephyr‑7B GGUF via ctransformers
• chat_once(user_msg) returns one reply string

This module is imported by app.py (Flask) — no CLI REPL code.
"""

import os
from pathlib import Path
from textwrap import shorten

from intent_emotion_router import analyse
from kbretriever import build_retriever
from tools.llm_loader import load_llm
from transformers import AutoTokenizer

# ───────────────────────── settings ─────────────────────────
CLASS_NAME       = os.getenv("WEAV_CLASS", "CarList")
CHUNK_MAX_CHARS  = 500
MAX_NEW_TOKENS   = 100
TEMPERATURE      = 0.5
MAX_PROMPT_TOKENS = 300

SCRIPT_DIR = Path(__file__).parent
PROMPT_TEMPLATE = (SCRIPT_DIR / "prompts" / "assistant_prompt.txt").read_text(encoding="utf-8")


_tok = AutoTokenizer.from_pretrained("HuggingFaceH4/zephyr-7b-beta", legacy=False)
llm  = load_llm()

# ───────────────────── helper: prompt build ─────────────────
def _count_tokens(text: str) -> int:
    return len(_tok.encode(text))

def build_prompt(user_msg: str, docs, intent: str, emotion: str) -> str:
    context_pieces, token_total = [], 0
    for d in docs[:2]:                                  # top‑2 chunks
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

# ───────────────────── public API: one turn ─────────────────
def chat_once(user_msg: str) -> str:
    # 1 Intent & emotion
    intent, emotion = analyse(user_msg)

    # 2 Category filter
    category = {"TechSupport": "Support",
                "SalesInquiry": "Sales"}.get(intent)

    # 3 Retrieve KB
    retriever = build_retriever(CLASS_NAME, category=category)
    docs      = retriever.invoke(user_msg)

    # 4 LLM generation
    prompt = build_prompt(user_msg, docs, intent, emotion)
    reply  = llm(prompt,
                 max_new_tokens=MAX_NEW_TOKENS,
                 temperature=TEMPERATURE,
                 stream=False)
    return reply.strip()
