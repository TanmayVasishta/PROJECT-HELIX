"""
HELIX Phase 3 -- Fast-Path Test Suite
Tests that don't require Ollama -- pure dispatcher validation.
Run: python tests/test_fastpath.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.middleware.file_manager import FileManager
from pathlib import Path


fm = FileManager()
PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}  {detail}")


# ---------------------------------------------------------------------------
# Fast-path pattern matching
# ---------------------------------------------------------------------------
print("\n" + "=" * 52)
print("  HELIX -- Fast-Path Pattern Tests")
print("=" * 52 + "\n")

print("[GROUP 1] Fast-path pattern matching (no LLM)")

tag, g = fm.fast_path_match("open chrome")
check("'open chrome' -> action=open", tag == "open", f"got {tag}")

tag, g = fm.fast_path_match("launch spotify")
check("'launch spotify' -> action=open", tag == "open", f"got {tag}")

tag, g = fm.fast_path_match("list downloads")
check("'list downloads' -> action=list", tag == "list", f"got {tag}")

tag, g = fm.fast_path_match("show my documents")
check("'show my documents' -> action=list", tag == "list", f"got {tag}")

tag, g = fm.fast_path_match("move report.pdf to documents")
check("'move ...' -> action=move", tag == "move", f"got {tag}")

tag, g = fm.fast_path_match("copy notes.txt to backup")
check("'copy ...' -> action=copy", tag == "copy", f"got {tag}")

tag, g = fm.fast_path_match("find pdfs in downloads")
check("'find ...' -> action=find", tag == "find", f"got {tag}")

tag, g = fm.fast_path_match("organize downloads")
check("'organize downloads' -> action=organize", tag == "organize", f"got {tag}")

tag, g = fm.fast_path_match("system health")
check("'system health' -> action=health", tag == "health", f"got {tag}")

tag, g = fm.fast_path_match("how's my system")
check("'how's my system' -> action=health", tag == "health", f"got {tag}")

tag, g = fm.fast_path_match("code mode")
check("'code mode' -> action=profile:code mode", tag == "profile:code mode", f"got {tag}")

tag, g = fm.fast_path_match("study mode")
check("'study mode' -> action=profile:study mode", tag == "profile:study mode", f"got {tag}")

tag, g = fm.fast_path_match("explain quantum computing")
check("'explain...' -> no fast-path match (None)", tag is None, f"got {tag}")


# ---------------------------------------------------------------------------
# Path resolver
# ---------------------------------------------------------------------------
print("\n[GROUP 2] Path resolution")

resolved = fm._resolve_path("downloads")
check("'downloads' resolves to Downloads folder",
      resolved == str(Path.home() / "Downloads"), f"got {resolved}")

resolved = fm._resolve_path("desktop")
check("'desktop' resolves to Desktop folder",
      resolved == str(Path.home() / "Desktop"), f"got {resolved}")

resolved = fm._resolve_path("documents")
check("'documents' resolves to Documents folder",
      resolved == str(Path.home() / "Documents"), f"got {resolved}")


# ---------------------------------------------------------------------------
# NL to glob conversion
# ---------------------------------------------------------------------------
print("\n[GROUP 3] NL-to-glob conversion")

check("'pdfs' -> '*.pdf'",        fm._nl_to_glob("pdfs")   == "*.pdf")
check("'python' -> '*.py'",       fm._nl_to_glob("python") == "*.py")
check("'*.txt' passthrough",      fm._nl_to_glob("*.txt")  == "*.txt")
check("'txt' -> '*.txt'",         fm._nl_to_glob("txt")    == "*.txt")
check("'csv' -> '*.csv'",         fm._nl_to_glob("csv")    == "*.csv")


# ---------------------------------------------------------------------------
# Destructive keyword detection
# ---------------------------------------------------------------------------
print("\n[GROUP 4] Destructive keyword gate")

check("'delete file.txt' is destructive",     fm.is_destructive("delete file.txt"))
check("'wipe my drive' is destructive",       fm.is_destructive("wipe my drive"))
check("'open chrome' is NOT destructive",     not fm.is_destructive("open chrome"))
check("'organize downloads' is NOT destructive", not fm.is_destructive("organize downloads"))


# ---------------------------------------------------------------------------
# System health (psutil live)
# ---------------------------------------------------------------------------
print("\n[GROUP 5] System health (live psutil)")

health = fm._action_system_health()
check("system health contains 'CPU'",  "CPU" in health)
check("system health contains 'RAM'",  "RAM" in health)
check("system health contains 'Disk'", "Disk" in health or "disk" in health.lower())


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
total = PASS + FAIL
print("\n" + "=" * 52)
print(f"  Results: {PASS}/{total} passed  |  {FAIL} failed")
print("=" * 52)
if FAIL == 0:
    print("  All tests passed. Fast-path ready.\n")
else:
    print(f"  {FAIL} test(s) FAILED -- review above.\n")
    sys.exit(1)
