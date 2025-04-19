# llm_loader.py
from ctransformers import AutoModelForCausalLM

GGUF_PATH = "models/zephyr-7b-beta.Q4_K_M.gguf"

def load_llm():
    return AutoModelForCausalLM.from_pretrained(
        GGUF_PATH,
        model_type="phi2",   # Zephyr is Mistral‑architecture
        context_length=8192,
        gpu_layers=0            # >0 if you have VRAM
    )