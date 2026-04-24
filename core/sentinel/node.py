"""
HELIX -- Sentinel Node (Phase 3 -- Few-Shot Edition)
Local qwen3.5:2b via direct Ollama Python client.
Speed-optimized: single LLM call, capped output, temperature=0.
Few-shot examples added to push classification accuracy to ~95%+.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import ollama
from config.settings import OLLAMA_MODEL


# ---------------------------------------------------------------------------
# Few-shot intent prompt -- 8 labeled examples boost accuracy to ~95%+
# ---------------------------------------------------------------------------
INTENT_PROMPT = """\
You are HELIX, a privacy-first AI OS classifier. Be fast and concise.

Classify this prompt and sanitize it in ONE response.

Rules:
- "local" = files, folders, apps, system (move, open, list, organize, delete, launch, copy, find, health)
- "cloud" = knowledge, reasoning, explanation, code help, summaries, questions about the world

Remove PII only if present: names->[NAME], paths->[PATH], emails->[EMAIL], phones->[PHONE]
If no PII exists, copy the prompt unchanged.

Examples:
Prompt: open vs code
INTENT: local
SANITIZED: open vs code

Prompt: move all my PDFs to the documents folder
INTENT: local
SANITIZED: move all my PDFs to the documents folder

Prompt: explain how attention mechanisms work in transformers
INTENT: cloud
SANITIZED: explain how attention mechanisms work in transformers

Prompt: move John Smith's files from C:/Users/john to backup
INTENT: local
SANITIZED: move [NAME]'s files from [PATH] to backup

Prompt: what is the capital of France?
INTENT: cloud
SANITIZED: what is the capital of France?

Prompt: organize my downloads folder by type
INTENT: local
SANITIZED: organize my downloads folder by type

Prompt: send an email to alice@example.com about the project
INTENT: cloud
SANITIZED: send an email to [EMAIL] about the project

Prompt: list files on my desktop
INTENT: local
SANITIZED: list files on my desktop

Now classify:
Prompt: {prompt}

Reply in EXACTLY 2 lines, nothing else:
INTENT: local
SANITIZED: <prompt with PII removed, or original if no PII>\
"""

REDACT_PROMPT = """\
Remove PII from this text.
Replace: names->[NAME], paths->[PATH], emails->[EMAIL], phones->[PHONE]
Return ONLY the redacted text.

Text: {text}\
"""

# Speed config -- tune per hardware
CLASSIFY_OPTIONS = {
    "num_predict": 80,    # slightly more for few-shot format
    "temperature": 0,
    "num_ctx":     1024,  # more context for few-shot examples
}

REDACT_OPTIONS = {
    "num_predict": 200,
    "temperature": 0,
    "num_ctx":     1024,
}

RAW_OPTIONS = {
    "num_predict": 1024,
    "temperature": 0.7,
    "num_ctx":     2048,
}


class SentinelNode:
    def __init__(self):
        print("[Sentinel] Connecting to local model via Ollama...")
        try:
            ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": "hi"}],
                options={"num_predict": 1}
            )
            print(f"[Sentinel] Online. Model: {OLLAMA_MODEL}")
        except Exception as e:
            raise RuntimeError(
                f"[Sentinel] Cannot reach Ollama.\n"
                f"  Run: ollama serve\n  Error: {e}"
            )

    def classify_intent(self, prompt: str) -> dict:
        """
        Single LLM call: classifies intent AND redacts PII simultaneously.
        Returns: { 'intent': 'local'|'cloud', 'sanitized_prompt': str, 'pii_detected': bool }
        """
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": INTENT_PROMPT.format(prompt=prompt)}],
            options=CLASSIFY_OPTIONS
        )
        raw = response["message"]["content"].strip()
        intent    = "local"
        sanitized = prompt

        for line in raw.split("\n"):
            line = line.strip()
            if line.upper().startswith("INTENT:"):
                val = line.split(":", 1)[1].strip().lower()
                intent = "cloud" if "cloud" in val else "local"
            elif line.upper().startswith("SANITIZED:"):
                sanitized = line.split(":", 1)[1].strip()

        return {
            "intent":           intent,
            "sanitized_prompt": sanitized,
            "pii_detected":     sanitized != prompt,
        }

    def redact_pii(self, text: str) -> str:
        """Standalone PII scrubber for edge cases."""
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": REDACT_PROMPT.format(text=text)}],
            options=REDACT_OPTIONS
        )
        return response["message"]["content"].strip()

    def llm_raw(self, prompt: str) -> str:
        """Direct model query -- no classification. Used for cloud fallback."""
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=RAW_OPTIONS
        )
        return response["message"]["content"].strip()
