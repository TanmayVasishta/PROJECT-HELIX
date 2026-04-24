"""
HELIX Phase 4 -- Fast-Path Test Suite for Chains
Tests that don't require Ollama or cloud APIs -- pure deterministic logic.

Run: python tests/test_chains.py
All tests should PASS without any LLM or internet connection.
"""
import sys
import os
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.chains.multi_step import HelixChainRunner
from core.chains.email_drafter import extract_email_topic


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
_results = []

def check(label: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f"  ({detail})" if detail else ""))
    _results.append(condition)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Chain detection -- research_and_save triggers
# ─────────────────────────────────────────────────────────────────────────────

def test_chain_detection_research():
    print("\n[Test 1] Chain detection -- research_and_save")
    cases = [
        "research machine learning and save",
        "research quantum computing and save to documents",
        "look up python decorators and save it",
        "find information about neural networks and save",
        "summarize transformers and save",
        "write a report on blockchain",
        "write a summary about HELIX project",
        "create a document on deep learning",
    ]
    for prompt in cases:
        name, groups = HelixChainRunner.detect(prompt)
        check(
            f"'{prompt}'",
            name == "research_and_save",
            f"got: {name!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Chain detection -- draft_email triggers
# ─────────────────────────────────────────────────────────────────────────────

def test_chain_detection_email():
    print("\n[Test 2] Chain detection -- draft_email")
    cases = [
        "draft an email about assignment extension",
        "draft email about project deadline",
        "write an email about attendance",
        "compose an email about internship application",
        "write email for leave request",
    ]
    for prompt in cases:
        name, groups = HelixChainRunner.detect(prompt)
        check(
            f"'{prompt}'",
            name == "draft_email",
            f"got: {name!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Chain detection -- non-chain prompts should NOT trigger
# ─────────────────────────────────────────────────────────────────────────────

def test_chain_no_false_positives():
    print("\n[Test 3] Chain detection -- no false positives")
    non_chain_prompts = [
        "open vs code",
        "list downloads",
        "system health",
        "hi",
        "explain how attention works",
        "what is the capital of France?",
        "organize my desktop",
        "move report.pdf to documents",
    ]
    for prompt in non_chain_prompts:
        name, _ = HelixChainRunner.detect(prompt)
        check(
            f"'{prompt}' should NOT be a chain",
            name is None,
            f"got: {name!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Topic extraction from chain regex groups
# ─────────────────────────────────────────────────────────────────────────────

def test_topic_extraction():
    print("\n[Test 4] Topic extraction from chain patterns")
    cases = [
        ("research machine learning and save", "machine learning"),
        ("research quantum computing and save to documents", "quantum computing"),
        ("summarize transformers and save", "transformers"),
    ]
    for prompt, expected_topic in cases:
        _, groups = HelixChainRunner.detect(prompt)
        topic = (groups[0] or "").strip() if groups else ""
        check(
            f"Topic from '{prompt}'",
            topic.lower() == expected_topic.lower(),
            f"got: {topic!r}, want: {expected_topic!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Email topic extractor
# ─────────────────────────────────────────────────────────────────────────────

def test_email_topic_extractor():
    print("\n[Test 5] Email topic extractor")
    cases = [
        ("draft an email about assignment extension", "assignment extension"),
        ("draft an email about project deadline", "project deadline"),
        ("write an email about attendance", "attendance"),
    ]
    for prompt, expected in cases:
        got = extract_email_topic(prompt)
        check(
            f"Email topic from '{prompt}'",
            expected.lower() in got.lower(),
            f"got: {got!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: FileManager.write_file
# ─────────────────────────────────────────────────────────────────────────────

def test_write_file():
    print("\n[Test 6] FileManager.write_file")
    from core.middleware.file_manager import FileManager

    fm = FileManager()
    test_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "_test_output")
    test_file = os.path.join(test_dir, "test_chain_output.txt")

    result = fm.write_file(test_file, "HELIX Phase 4 test content.\nLine 2.\n")
    check(
        "write_file returns success message",
        "[FileManager] Written:" in result,
        result
    )
    check(
        "File actually exists on disk",
        os.path.exists(test_file),
    )

    # Cleanup
    try:
        shutil.rmtree(test_dir)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Safe filename generation
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_filename():
    print("\n[Test 7] Safe filename generation from _safe_filename()")
    from core.chains.multi_step import _safe_filename

    cases = [
        "machine learning",
        "Quantum Computing!",
        "python decorators & closures",
        "HELIX: a privacy OS",
    ]
    for topic in cases:
        fname = _safe_filename(topic)
        # Should be alphanumeric + underscores, end with date + .txt
        ok = fname.endswith(".txt") and " " not in fname and ":" not in fname
        check(f"Safe filename for '{topic}'", ok, fname)


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  HELIX Phase 4 -- Chain Test Suite")
    print("  (No LLM or API keys required)")
    print("=" * 60)

    test_chain_detection_research()
    test_chain_detection_email()
    test_chain_no_false_positives()
    test_topic_extraction()
    test_email_topic_extractor()
    test_write_file()
    test_safe_filename()

    passed = sum(_results)
    total  = len(_results)
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} passed", end="")
    if passed == total:
        print("  \033[92m-- ALL PASS\033[0m")
    else:
        print(f"  \033[91m-- {total - passed} FAILED\033[0m")
    print("=" * 60)
