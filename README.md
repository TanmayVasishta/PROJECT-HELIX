# HELIX — Hybrid Environment for Localized Intelligence and eXecution

Privacy-first AI Operating System middleware.
Local Sentinel (Llama3) + Cloud Oracle (Gemini) + ChromaDB memory.

---

## Quick Start

### 1. Make sure Ollama is running
```
ollama serve
```

### 2. Add your Gemini API key
Edit `config/settings.py` and replace `YOUR_GEMINI_API_KEY_HERE`

### 3. Run CLI mode
```
cd C:\Users\tanma\HELIX
python main.py
```

### 4. Run GUI mode (PyQt6 HUD)
```
python launch_hud.py
```

### 5. Run Phase 2 tests
```
python tests/test_sentinel.py
```

---

## Project Structure

```
HELIX/
├── main.py               # CLI entry point
├── launch_hud.py         # GUI entry point
├── requirements.txt
├── config/
│   └── settings.py       # API keys, model config
├── core/
│   ├── sentinel/
│   │   └── node.py       # Local Llama3 — intent + PII redaction
│   ├── oracle/
│   │   └── cloud.py      # Gemini API — cloud reasoning
│   ├── router/
│   │   └── router.py     # Pipeline orchestrator
│   ├── memory/
│   │   └── memory.py     # ChromaDB local RAG
│   └── middleware/
│       └── file_manager.py  # OS automation + Watchdog
├── voice/
│   └── listener.py       # Mic capture via sounddevice
├── ui/
│   └── hud.py            # PyQt6 non-blocking HUD
├── data/
│   └── chromadb/         # Persistent vector store (auto-created)
├── logs/                 # Log files (Phase 6)
└── tests/
    └── test_sentinel.py  # Phase 2 Sentinel tests
```

---

## Phase Roadmap

| Phase | Weeks | Status |
|-------|-------|--------|
| 1 — Environment + Scaffold | 1-3 | ✅ DONE |
| 2 — Sentinel + ChromaDB | 4-7 | 🔜 NEXT |
| 3 — File Middleware + PII tuning | 8-10 | ⏳ |
| 4 — Cloud routing + LangChain | 11-13 | ⏳ |
| 5 — Voice HUD + async | 14-16 | ⏳ |
| 6 — Testing + Docs | 17-18 | ⏳ |

---

## Tech Stack

- **Sentinel Node**: Llama3 via Ollama (local, offline)
- **Cloud Oracle**: Google Gemini 2.0 Flash (`google-genai`)
- **Memory**: ChromaDB (persistent, local vector store)
- **Routing**: LangChain + custom router
- **UI**: PyQt6 (non-blocking with QThread workers)
- **Voice**: sounddevice + SpeechRecognition + Whisper
- **OS Automation**: watchdog + shutil + subprocess
