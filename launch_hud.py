"""
HELIX — GUI Entry Point
Launches the PyQt6 HUD with the full router connected.
Run: python launch_hud.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.router.router import HelixRouter
from ui.hud import launch_hud

if __name__ == "__main__":
    print("[HELIX] Starting GUI mode...")
    try:
        router = HelixRouter()
    except Exception as e:
        print(f"[HELIX] Router init failed: {e}")
        print("Make sure Ollama is running: ollama serve")
        sys.exit(1)
    launch_hud(router=router)
