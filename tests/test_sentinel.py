"""
HELIX Phase 2 Test Suite — Sentinel Node
Run: python tests/test_sentinel.py
Ollama must be running with llama3 pulled.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.sentinel.node import SentinelNode


def test_intent_local():
    sentinel = SentinelNode()
    result = sentinel.classify_intent("move all my PDFs to the documents folder")
    print(f"  Input : move all my PDFs to the documents folder")
    print(f"  Intent: {result['intent']}  (expected: local)")
    print(f"  Sanitized: {result['sanitized_prompt']}")
    assert result["intent"] == "local", f"FAIL: expected local, got {result['intent']}"
    print("  ✅ PASS\n")


def test_intent_cloud():
    sentinel = SentinelNode()
    result = sentinel.classify_intent("explain how transformers work in deep learning")
    print(f"  Input : explain how transformers work in deep learning")
    print(f"  Intent: {result['intent']}  (expected: cloud)")
    print(f"  Sanitized: {result['sanitized_prompt']}")
    assert result["intent"] == "cloud", f"FAIL: expected cloud, got {result['intent']}"
    print("  ✅ PASS\n")


def test_pii_redaction():
    sentinel = SentinelNode()
    raw = "Move John Smith's files from C:/Users/john/Desktop to the backup folder"
    result = sentinel.redact_pii(raw)
    print(f"  Input : {raw}")
    print(f"  Output: {result}")
    assert "John Smith" not in result, "FAIL: PII not redacted"
    assert "john" not in result.lower() or "[" in result, "FAIL: path not redacted"
    print("  ✅ PASS\n")


if __name__ == "__main__":
    print("=" * 50)
    print("  HELIX — Sentinel Node Test Suite")
    print("=" * 50 + "\n")

    print("[TEST 1] Local intent classification")
    test_intent_local()

    print("[TEST 2] Cloud intent classification")
    test_intent_cloud()

    print("[TEST 3] PII redaction")
    test_pii_redaction()

    print("=" * 50)
    print("  All tests passed. Sentinel Node is ready.")
    print("=" * 50)
