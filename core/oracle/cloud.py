"""
HELIX -- Cloud Oracle (Multi-Provider)
Tries providers in order: Groq -> DeepSeek -> OpenRouter -> Gemini
All use OpenAI-compatible API except Gemini.
Only receives PII-free, sanitized prompts from Sentinel Node.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.settings import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    DEEPSEEK_API_KEY,
    OPENROUTER_API_KEY,
)


def _openai_compat_query(base_url: str, api_key: str, model: str, prompt: str) -> str:
    """Generic OpenAI-compatible chat completion."""
    import urllib.request
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.7,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"].strip()


class CloudOracle:
    """
    Multi-provider cloud oracle.
    Provider priority: Groq > DeepSeek > OpenRouter > Gemini
    Falls back automatically if a provider fails or has quota issues.
    """

    PROVIDERS = [
        {
            "name": "Groq",
            "type": "openai_compat",
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "key_attr": "GROQ_API_KEY",
        },
        {
            "name": "DeepSeek",
            "type": "openai_compat",
            "base_url": "https://api.deepseek.com",
            "model": "deepseek-chat",
            "key_attr": "DEEPSEEK_API_KEY",
        },
        {
            "name": "OpenRouter",
            "type": "openai_compat",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "google/gemma-4-31b-it:free",
            "key_attr": "OPENROUTER_API_KEY",
        },
        {
            "name": "Gemini",
            "type": "gemini",
            "model": "gemini-2.0-flash",
            "key_attr": "GEMINI_API_KEY",
        },
    ]

    KEYS = {
        "GROQ_API_KEY":       GROQ_API_KEY,
        "DEEPSEEK_API_KEY":   DEEPSEEK_API_KEY,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "GEMINI_API_KEY":     GEMINI_API_KEY,
    }

    def __init__(self):
        self.active_provider = None
        # Find first provider with a real key configured
        for p in self.PROVIDERS:
            key = self.KEYS.get(p["key_attr"], "")
            if key and not key.startswith("YOUR_"):
                self.active_provider = p["name"]
                break
        if self.active_provider:
            print(f"[Oracle] Primary provider: {self.active_provider}")
        else:
            print("[Oracle] WARNING: No API keys configured. Cloud routing disabled.")

    def query(self, sanitized_prompt: str) -> str:
        """
        Send PII-free prompt to cloud. Tries each configured provider in order.
        """
        if not sanitized_prompt.strip():
            return "[Oracle] Empty prompt."

        errors = []
        for provider in self.PROVIDERS:
            key = self.KEYS.get(provider["key_attr"], "")
            if not key or key.startswith("YOUR_"):
                continue   # skip unconfigured providers

            try:
                if provider["type"] == "openai_compat":
                    result = _openai_compat_query(
                        provider["base_url"], key,
                        provider["model"], sanitized_prompt
                    )
                else:
                    result = self._query_gemini(key, provider["model"], sanitized_prompt)

                if self.active_provider != provider["name"]:
                    print(f"[Oracle] Switched to: {provider['name']}")
                    self.active_provider = provider["name"]
                return result

            except Exception as e:
                err = str(e)
                errors.append(f"{provider['name']}: {err[:120]}")
                # Skip on ANY error and try next provider
                print(f"[Oracle] {provider['name']} failed: {err[:80]}")
                continue

        # All providers failed
        err_summary = " | ".join(errors)
        return (
            f"[Oracle] All cloud providers unavailable.\n"
            f"Errors: {err_summary}\n"
            f"Tip: Add a free Groq key at console.groq.com -> config/settings.py GROQ_API_KEY"
        )

    def _query_gemini(self, api_key: str, model: str, prompt: str) -> str:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text

    def status(self) -> str:
        configured = [
            p["name"] for p in self.PROVIDERS
            if self.KEYS.get(p["key_attr"], "").startswith("YOUR_") is False
            and self.KEYS.get(p["key_attr"], "")
        ]
        return f"Configured providers: {', '.join(configured) if configured else 'None'}"
