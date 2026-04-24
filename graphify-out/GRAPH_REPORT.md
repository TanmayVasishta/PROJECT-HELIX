# Graph Report - HELIX  (2026-04-24)

## Corpus Check
- 34 files · ~28,486 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 206 nodes · 328 edges · 15 communities detected
- Extraction: 64% EXTRACTED · 36% INFERRED · 0% AMBIGUOUS · INFERRED: 117 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]

## God Nodes (most connected - your core abstractions)
1. `FileManager` - 29 edges
2. `ProfileManager` - 20 edges
3. `HelixRouter` - 18 edges
4. `EmailDrafter` - 14 edges
5. `SentinelNode` - 13 edges
6. `HelixChainRunner` - 12 edges
7. `HelixHUD` - 11 edges
8. `CloudOracle` - 10 edges
9. `HelixAuditLog` - 9 edges
10. `HelixMemory` - 9 edges

## Surprising Connections (you probably didn't know these)
- `HELIX -- Main Entry Point (Phase 3) CLI mode with Watchdog active on Downloads +` --uses--> `HelixRouter`  [INFERRED]
  main.py → core\router\router.py
- `Called by Watchdog threads -- printed inline during HELIX session.` --uses--> `HelixRouter`  [INFERRED]
  main.py → core\router\router.py
- `HELIX -- Multi-Step Chain Runner (Phase 4) LangChain-style sequential task autom` --uses--> `EmailDrafter`  [INFERRED]
  core\chains\multi_step.py → core\chains\email_drafter.py
- `Convert a topic string to a safe filename.` --uses--> `EmailDrafter`  [INFERRED]
  core\chains\multi_step.py → core\chains\email_drafter.py
- `Multi-step chain executor for Phase 4.     Requires oracle, sentinel, file_manag` --uses--> `EmailDrafter`  [INFERRED]
  core\chains\multi_step.py → core\chains\email_drafter.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.11
Nodes (14): Execute a parsed action dict using FileManager methods.         Returns a respon, FileManager, Try to match prompt against FAST_PATH_PATTERNS.         Returns (action_tag, mat, Main dispatcher.         If action_tag is provided (fast-path), dispatch immedia, Main dispatcher.         If action_tag is provided (fast-path), dispatch immedia, Find and delete files/shortcuts.         Supports:           - Bulk mode: "all s, Resolve common folder names + absolute paths from free text.         Returns res, Convert natural language like 'pdfs' or '*.py' to glob pattern. (+6 more)

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (15): HelixAuditLog, HELIX -- Structured Audit Log (Phase 3 Major Feature) Append-only JSON-lines aud, CloudCommandParser, HELIX -- Cloud Command Parser (Phase 4 Enhancement) Uses Cloud Oracle to interpr, Sends unrecognised local OS commands to the Cloud Oracle for NLP parsing.     Re, HELIX — GUI Entry Point Launches the PyQt6 HUD with the full router connected. R, Called by Watchdog threads -- printed inline during HELIX session., HelixMemory (+7 more)

### Community 2 - "Community 2"
Cohesion: 0.15
Nodes (7): HelixHUD, HelixWorker, launch_hud(), HELIX — Voice HUD (Phase 5 full implementation) PyQt6 non-blocking UI with async, Runs router.process() in background thread., QMainWindow, QObject

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (9): CloudOracle, _openai_compat_query(), HELIX -- Cloud Oracle (Multi-Provider) Tries providers in order: Groq -> DeepSee, Generic OpenAI-compatible chat completion., Multi-provider cloud oracle.     Provider priority: Groq > DeepSeek > OpenRouter, Send PII-free prompt to cloud. Tries each configured provider in order., Ask the cloud AI to parse the prompt into a structured action dict.         Retu, Fetch relevant past interactions as context string. (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.24
Nodes (13): detect(), HELIX -- Multi-Step Chain Runner (Phase 4) LangChain-style sequential task autom, Convert a topic string to a safe filename., _safe_filename(), check(), HELIX Phase 4 -- Fast-Path Test Suite for Chains Tests that don't require Ollama, test_chain_detection_email(), test_chain_detection_research() (+5 more)

### Community 5 - "Community 5"
Cohesion: 0.19
Nodes (9): EmailDrafter, extract_email_topic(), HELIX -- Email Drafter (Phase 4) Privacy-safe Gmail drafting pipeline.  Flow:, Open Gmail compose in the default browser., Extract the email topic from the sanitized prompt.     e.g. "draft an email abou, Privacy-safe email drafting module.     Requires a CloudOracle instance and a Se, Full drafting pipeline.          Returns a dict:           {             'topic', Check if prompt matches a chain pattern.         Returns (chain_name, regex_grou (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (9): HelixWatcher, HELIX -- File Management Middleware (Phase 3) Regex fast-path + NL action dispat, Passive filesystem monitor.     Calls callback with a human-readable string on f, start_watcher(), FileSystemEventHandler, main(), proactive_notify(), HELIX -- Main Entry Point (Phase 3) CLI mode with Watchdog active on Downloads + (+1 more)

### Community 7 - "Community 7"
Cohesion: 0.23
Nodes (8): HELIX -- Sentinel Node (Phase 3 -- Few-Shot Edition) Local qwen3.5:2b via direct, Single LLM call: classifies intent AND redacts PII simultaneously.         Retur, Standalone PII scrubber for edge cases., SentinelNode, HELIX Phase 2 Test Suite — Sentinel Node Run: python tests/test_sentinel.py Olla, test_intent_cloud(), test_intent_local(), test_pii_redaction()

### Community 8 - "Community 8"
Cohesion: 0.17
Nodes (5): Return last n log entries as a human-readable table., Quick stats -- total calls, PII rate, cloud rate., Try to match prompt against FAST_PATH_PATTERNS.         Returns (action_tag, mat, Direct model query -- no classification. Used for cloud fallback., Full HELIX pipeline:         0.  Special command shortcuts (audit log, stats)

### Community 9 - "Community 9"
Cohesion: 0.29
Nodes (4): HELIX — Voice Listener (Phase 5 full implementation) Uses sounddevice + SpeechRe, Captures microphone audio via sounddevice and converts to text     via SpeechRec, Records audio for up to `timeout` seconds.         Returns transcribed text or e, VoiceListener

### Community 10 - "Community 10"
Cohesion: 0.4
Nodes (1): Test all available free API alternatives for HELIX Cloud Oracle Run: python test

### Community 11 - "Community 11"
Cohesion: 0.67
Nodes (1): HELIX Phase 3 -- Fast-Path Test Suite Tests that don't require Ollama -- pure di

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Multi-provider cloud oracle.     Provider priority: Groq > DeepSeek > OpenRouter

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Send PII-free prompt to cloud. Tries each configured provider in order.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Full HELIX pipeline:         1. Special command shortcuts (audit log, stats)

## Knowledge Gaps
- **40 isolated node(s):** `Test all available free API alternatives for HELIX Cloud Oracle Run: python test`, `HELIX -- Email Drafter (Phase 4) Privacy-safe Gmail drafting pipeline.  Flow:`, `Extract the email topic from the sanitized prompt.     e.g. "draft an email abou`, `Privacy-safe email drafting module.     Requires a CloudOracle instance and a Se`, `Full drafting pipeline.          Returns a dict:           {             'topic'` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 10`** (5 nodes): `test_apis.py`, `Test all available free API alternatives for HELIX Cloud Oracle Run: python test`, `test_deepseek()`, `test_groq()`, `test_together()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (3 nodes): `test_fastpath.py`, `check()`, `HELIX Phase 3 -- Fast-Path Test Suite Tests that don't require Ollama -- pure di`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Multi-provider cloud oracle.     Provider priority: Groq > DeepSeek > OpenRouter`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Send PII-free prompt to cloud. Tries each configured provider in order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Full HELIX pipeline:         1. Special command shortcuts (audit log, stats)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `FileManager` connect `Community 0` to `Community 1`, `Community 4`, `Community 6`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Why does `HelixRouter` connect `Community 1` to `Community 0`, `Community 3`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `ProfileManager` connect `Community 0` to `Community 8`, `Community 6`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `FileManager` (e.g. with `ProfileManager` and `HelixRouter`) actually correct?**
  _`FileManager` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `ProfileManager` (e.g. with `FileManager` and `HelixWatcher`) actually correct?**
  _`ProfileManager` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `HelixRouter` (e.g. with `HELIX -- Main Entry Point (Phase 3) CLI mode with Watchdog active on Downloads +` and `Called by Watchdog threads -- printed inline during HELIX session.`) actually correct?**
  _`HelixRouter` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `EmailDrafter` (e.g. with `HelixChainRunner` and `HELIX -- Multi-Step Chain Runner (Phase 4) LangChain-style sequential task autom`) actually correct?**
  _`EmailDrafter` has 9 INFERRED edges - model-reasoned connections that need verification._