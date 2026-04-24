"""
Test all available free API alternatives for HELIX Cloud Oracle
Run: python test_apis.py
"""
import urllib.request
import json

# ── DeepSeek ──────────────────────────────────────────────
def test_deepseek(api_key):
    url = "https://api.deepseek.com/chat/completions"
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "say hi in 3 words"}],
        "max_tokens": 20
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return "OK", data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "ERR", str(e)[:120]

# ── Groq (free, very fast) ─────────────────────────────────
def test_groq(api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": "say hi in 3 words"}],
        "max_tokens": 20
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return "OK", data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "ERR", str(e)[:120]

# ── Together AI (free tier) ────────────────────────────────
def test_together(api_key):
    url = "https://api.together.xyz/v1/chat/completions"
    payload = json.dumps({
        "model": "meta-llama/Llama-3-8b-chat-hf",
        "messages": [{"role": "user", "content": "say hi in 3 words"}],
        "max_tokens": 20
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return "OK", data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "ERR", str(e)[:120]

if __name__ == "__main__":
    print("=" * 55)
    print("  HELIX -- Cloud Oracle API Test Suite")
    print("=" * 55)

    # ── Replace these with your keys ──
    DEEPSEEK_KEY = "YOUR_DEEPSEEK_KEY"
    GROQ_KEY     = "YOUR_GROQ_KEY"
    TOGETHER_KEY = "YOUR_TOGETHER_KEY"
    # ──────────────────────────────────

    status, result = test_deepseek(DEEPSEEK_KEY)
    print(f"\nDeepSeek  [{status}]: {result}")

    status, result = test_groq(GROQ_KEY)
    print(f"Groq      [{status}]: {result}")

    status, result = test_together(TOGETHER_KEY)
    print(f"Together  [{status}]: {result}")

    print("\n" + "=" * 55)
