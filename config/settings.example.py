# ─────────────────────────────────────────
#  HELIX Configuration  (EXAMPLE FILE)
#  Copy this to settings.py and fill in your keys
# ─────────────────────────────────────────
from pathlib import Path

# Local Sentinel Node (Ollama)
OLLAMA_MODEL    = "qwen3.5:2b"
OLLAMA_BASE_URL = "http://localhost:11434"

# ── Cloud Oracle -- Multi-Provider ──────────────────────────
# Groq (free, blazing fast) -- console.groq.com
GROQ_API_KEY = "YOUR_GROQ_KEY"

# DeepSeek (great reasoning) -- platform.deepseek.com
DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_KEY"

# OpenRouter (free model aggregator) -- openrouter.ai
OPENROUTER_API_KEY = "YOUR_OPENROUTER_KEY"

# Gemini (last fallback) -- aistudio.google.com
GEMINI_API_KEY = "YOUR_GEMINI_KEY"

# Memory
CHROMA_DB_PATH = "./data/chromadb"

# Voice
WAKE_WORD = "helix"

# Safety
CONFIRMATION_REQUIRED = True

# Logging
LOG_LEVEL = "INFO"

# ── Phase 4 -- Multi-Step Chains ────────────────────────
CHAIN_OUTPUT_DIR = str(Path.home() / "Documents" / "HELIX_Outputs")
CHAIN_MAX_TOKENS = 1500
GMAIL_COMPOSE_URL = "https://mail.google.com/mail/?view=cm&fs=1&su={subject}&body={body}"
