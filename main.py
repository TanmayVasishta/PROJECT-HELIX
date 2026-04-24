"""
HELIX -- Main Entry Point (Phase 4)
CLI mode with Watchdog active on Downloads + Desktop.
Phase 4 adds multi-step chain automation: research+save, email drafting.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.router.router import HelixRouter
from core.middleware.file_manager import start_watcher
from pathlib import Path


BANNER = """
==========================================
   H E L I X  v0.4  --  ONLINE
   Privacy-First AI Operating System
   Local  : qwen3.5:2b (Ollama)
   Cloud  : Groq -> DeepSeek -> OpenRouter -> Gemini
   Memory : ChromaDB (local)
   Fast   : Regex fast-path ACTIVE
   Chains : Multi-step automation ACTIVE
==========================================
Commands: 'audit log' | 'audit stats' | 'quit'
Chains  : 'research X and save' | 'draft an email about X'
"""

# Folders monitored proactively by Watchdog
WATCH_FOLDERS = [
    str(Path.home() / "Downloads"),
    str(Path.home() / "Desktop"),
]


def proactive_notify(msg: str):
    """Called by Watchdog threads -- printed inline during HELIX session."""
    print(f"\n  [HELIX-WATCH] {msg}")
    print("> ", end="", flush=True)  # Restore prompt


def main():
    print(BANNER)

    try:
        router = HelixRouter()
    except Exception as e:
        print(f"[HELIX] Startup failed: {e}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)

    # Start Watchdog on Downloads + Desktop
    watchers = []
    for folder in WATCH_FOLDERS:
        if Path(folder).exists():
            try:
                w = start_watcher(folder, proactive_notify)
                watchers.append(w)
            except Exception as e:
                print(f"[Watcher] Could not monitor {folder}: {e}")

    print()  # spacing after watcher init

    # Main command loop
    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        response = router.process(user_input)
        print(f"\n[HELIX] {response}")

    # Graceful shutdown
    for w in watchers:
        try:
            w.stop()
            w.join()
        except Exception:
            pass
    print("\n[HELIX] Shutting down. Goodbye.")


if __name__ == "__main__":
    main()
