from pathlib import Path
from ctransformers import AutoModelForCausalLM

GGUF_PATH = str(Path(__file__).parent.parent / "models" / "zephyr-7b-beta.Q4_K_M.gguf")

def load_llm():
    return AutoModelForCausalLM.from_pretrained(
        GGUF_PATH,
        model_type="mistral",   # Zephyr is Mistral‑architecture
        context_length=8192,
        gpu_layers=28,# >0 if you have VRAM                      
    )


