"""
HELIX -- File Management Middleware (Phase 3)
Regex fast-path + NL action dispatcher + system health.
All operations are deterministic -- no LLM calls here.
"""
import os
import re
import shutil
import subprocess
import psutil
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ---------------------------------------------------------------------------
# Destructive keyword gate
# ---------------------------------------------------------------------------
DESTRUCTIVE_KEYWORDS = [
    "delete", "remove", "wipe", "erase", "overwrite", "format", "uninstall", "rmdir"
]

# ---------------------------------------------------------------------------
# App registry -- maps spoken aliases to launch commands
# ---------------------------------------------------------------------------
APP_MAP = {
    # Editors / IDEs
    "vscode":       "code",
    "vs code":      "code",
    "code":         "code",
    "cursor":       "cursor",
    "notepad":      "notepad",
    "notepad++":    "notepad++",
    # Browsers
    "chrome":       "chrome",
    "browser":      "chrome",
    "edge":         "msedge",
    "firefox":      "firefox",
    # Communication
    "discord":      "discord",
    "whatsapp":     r"C:\Users\tanma\AppData\Local\WhatsApp\WhatsApp.exe",
    "teams":        "msteams",
    # Music / media
    "spotify":      "spotify",
    "vlc":          "vlc",
    "obs":          "obs64",
    # System tools
    "explorer":         "explorer",
    "file explorer":    "explorer",
    "terminal":         "wt",
    "windows terminal": "wt",
    "powershell":       "powershell",
    "task manager":     "taskmgr",
    "settings":         "ms-settings:",
    "calculator":       "calc",
    "paint":            "mspaint",
    # Dev / task tools
    "notion":       "notion",
    "warp":         "warp",
    "postman":      "postman",
}

# ---------------------------------------------------------------------------
# Regex fast-path patterns -- matched before ANY LLM call
# Format: (compiled_pattern, action_tag)
# ---------------------------------------------------------------------------
FAST_PATH_PATTERNS = [
    # "delete discord from desktop", "remove file.txt", "delete report from downloads"
    (re.compile(r"^(?:delete|remove|erase)\s+(.+?)(?:\s+(?:from|on|off)\s+(.+))?$", re.I), "delete"),
    # Greetings / conversational -- instant local response, no LLM
    (re.compile(r"^(?:hi|hey|hello|sup|yo|greetings)[\s!.]*$", re.I), "greet"),
    # Help requests
    (re.compile(r"^(?:help|i need help|what can you do|commands|helix help|\?)[\s!.]*$", re.I), "help"),
    # "open chrome", "launch spotify", "start vs code"
    (re.compile(r"^(?:open|launch|start|run)\s+(.+)$", re.I), "open"),
    # "list downloads", "show C:\\Users\\tanma\\Desktop", "list my documents"
    (re.compile(r"^(?:list|show|ls)\s+(?:my\s+)?(.+)$", re.I), "list"),
    # "move report.pdf to Documents", "move file from downloads to desktop"
    (re.compile(r"^move\s+(.+?)\s+(?:from\s+.+?\s+)?to\s+(.+)$", re.I), "move"),
    # "copy notes.txt to backup"
    (re.compile(r"^copy\s+(.+?)\s+to\s+(.+)$", re.I), "copy"),
    # "find pdfs in downloads", "find *.py in projects"
    (re.compile(r"^find\s+(.+?)\s+in\s+(.+)$", re.I), "find"),
    # "organize downloads", "sort my desktop by type"
    (re.compile(r"^(?:organize|sort)\s+(?:my\s+)?(.+?)(?:\s+by\s+type)?$", re.I), "organize"),
    # "system health", "how's my system", "show system stats"
    (re.compile(r"^(?:system\s+health|how.?s\s+my\s+system|system\s+stats?|show\s+system)$", re.I), "health"),
    # Workflow profile triggers
    (re.compile(r"^(?:activate\s+)?code\s+mode$", re.I), "profile:code mode"),
    (re.compile(r"^(?:activate\s+)?study\s+mode$", re.I), "profile:study mode"),
    (re.compile(r"^(?:activate\s+)?presentation\s+mode$", re.I), "profile:presentation mode"),
    (re.compile(r"^(?:activate\s+)?focus\s+mode$", re.I), "profile:focus mode"),
    # "save that to notes.txt" / "save to documents" -- for chain post-processing
    (re.compile(r"^save\s+(?:that\s+)?(?:to|in)\s+(.+)$", re.I), "save_last"),
    # "how many files on my desktop", "count shortcuts", "what's on my desktop"
    (re.compile(
        r"^(?:how many|count|what(?:'s| is| are)(?: (?:on|in))?|list(?:all)?)\s+"
        r"(?:[\w\s]+?\s+)?(?:on|in)\s+(?:my\s+)?(desktop|downloads|documents|pictures|videos|music|home)$",
        re.I
    ), "list_context"),
    # "what are the shortcuts on my desktop", "show me what's on my desktop"
    (re.compile(
        r"^(?:show me|tell me|give me|what are)\s+(?:the\s+)?(?:[\w\s]+?\s+)?(?:on|in)\s+(?:my\s+)?(desktop|downloads|documents|pictures|videos|music).*$",
        re.I
    ), "list_context"),
]

# Common folder shortcuts -- resolved to absolute paths
COMMON_DIRS = {
    "downloads":    str(Path.home() / "Downloads"),
    "desktop":      str(Path.home() / "Desktop"),
    "documents":    str(Path.home() / "Documents"),
    "pictures":     str(Path.home() / "Pictures"),
    "music":        str(Path.home() / "Music"),
    "videos":       str(Path.home() / "Videos"),
    "home":         str(Path.home()),
}

# Organize: extension -> folder name
EXT_CATEGORY = {
    "images":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"},
    "documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".ppt", ".pptx", ".xls", ".xlsx", ".odt"},
    "videos":    {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"},
    "audio":     {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "code":      {".py", ".js", ".ts", ".html", ".css", ".java", ".cpp", ".c", ".rs", ".go", ".sh", ".ps1"},
    "archives":  {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "data":      {".csv", ".json", ".xml", ".sql", ".db"},
}


class FileManager:

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def is_destructive(self, prompt: str) -> bool:
        return any(kw in prompt.lower() for kw in DESTRUCTIVE_KEYWORDS)

    def fast_path_match(self, prompt: str):
        """
        Try to match prompt against FAST_PATH_PATTERNS.
        Returns (action_tag, match_groups) or (None, None) if no match.
        Called by the Router BEFORE sending to Sentinel -- 0ms response.
        """
        for pattern, action in FAST_PATH_PATTERNS:
            m = pattern.match(prompt.strip())
            if m:
                return action, m.groups()
        return None, None

    def execute(self, prompt: str, action_tag: str = None, groups: tuple = None) -> str:
        """
        Main dispatcher.
        If action_tag is provided (fast-path), dispatch immediately.
        Otherwise fallback to keyword scan (legacy path -- kept for safety).
        """
        if action_tag:
            return self._dispatch(action_tag, groups or ())

        # Legacy keyword fallback (for edge cases LLM sends through)
        pl = prompt.lower().strip()
        for keyword, cmd in APP_MAP.items():
            if keyword in pl and any(w in pl for w in ("open", "launch", "start", "run")):
                return self._action_open(keyword)

        if any(w in pl for w in ("list", "show", "ls")):
            path = self._resolve_path(pl) or str(Path.home())
            return self._action_list(path)

        # Natural language queries about folder contents (e.g. "what apps are on my desktop")
        for folder_name, folder_path in COMMON_DIRS.items():
            if folder_name in pl:
                if any(w in pl for w in (
                    "what", "how many", "count", "shortcut", "contents",
                )):
                    # Special: count + filter by extension
                    folder_p = Path(folder_path)
                    if not folder_p.exists():
                        return f"[FileManager] Folder not found: {folder_path}"
                    items = list(folder_p.iterdir())
                    if any(w in pl for w in ("shortcut", "app", "lnk")):
                        items = [i for i in items if i.suffix.lower() == ".lnk"]
                        if not items:
                            return f"[FileManager] No app shortcuts (.lnk) found on {folder_name}."
                        names = "\n".join(f"  - {i.stem}" for i in sorted(items, key=lambda x: x.name.lower()))
                        return f"[FileManager] {len(items)} app shortcut(s) on your {folder_name}:\n{names}"
                    lines = [f"  {'[DIR]' if i.is_dir() else '[FILE]'} {i.name}" for i in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))[:30]]
                    header = f"[FileManager] {folder_name.capitalize()} — {len(items)} item(s):"
                    return header + "\n" + "\n".join(lines)

        # Signal the Router to escalate this to the Cloud Oracle
        return "__ESCALATE_TO_CLOUD__"

    # -----------------------------------------------------------------------
    # Dispatcher
    # -----------------------------------------------------------------------

    def _dispatch(self, action: str, groups: tuple) -> str:
        if action == "greet":
            return "[HELIX] Hey! Ready to work. Try: 'open vs code', 'list downloads', 'system health', or 'help'."
        elif action == "help":
            return (
                "[HELIX] Available commands (all instant, no LLM wait):\n"
                "  open [app]              -- launch any app (vs code, chrome, spotify...)\n"
                "  list [folder]           -- show folder contents\n"
                "  find [type] in [folder] -- search for files\n"
                "  move [file] to [folder] -- move files\n"
                "  copy [file] to [folder] -- copy files\n"
                "  organize [folder]       -- sort files into category subfolders\n"
                "  system health           -- CPU / RAM / disk report\n"
                "  code mode               -- launch coding workspace\n"
                "  study mode              -- launch study workspace\n"
                "  audit log               -- show recent HELIX activity\n"
                "  audit stats             -- show usage statistics\n"
                "  [anything else]         -- routed to local AI or Gemini cloud"
            )
        elif action == "delete":
            target = groups[0] if groups else ""
            location = groups[1] if len(groups) > 1 and groups[1] else ""
            return self._action_delete(target, location)
        elif action == "open":
            return self._action_open(groups[0] if groups else "")
        elif action == "list":
            return self._action_list(groups[0] if groups else str(Path.home()))
        elif action == "move":
            src, dst = (groups[0], groups[1]) if len(groups) >= 2 else ("", "")
            return self._action_move(src, dst)
        elif action == "copy":
            src, dst = (groups[0], groups[1]) if len(groups) >= 2 else ("", "")
            return self._action_copy(src, dst)
        elif action == "find":
            pattern, folder = (groups[0], groups[1]) if len(groups) >= 2 else ("*", str(Path.home()))
            return self._action_find(pattern, folder)
        elif action == "organize":
            folder = groups[0] if groups else str(Path.home() / "Downloads")
            return self._action_organize(folder)
        elif action == "health":
            return self._action_system_health()
        elif action == "save_last":
            dest_hint = groups[0] if groups else ""
            return f"[FileManager] 'save last' requires a chain context. Use: 'research X and save to {dest_hint}'"
        elif action.startswith("profile:"):
            profile_name = action.split(":", 1)[1]
            return self._action_profile(profile_name)
        elif action == "list_context":
            # Folder name is in groups[0] from the regex capture
            folder_name = (groups[0] or "").strip().lower() if groups else ""
            folder_path = COMMON_DIRS.get(folder_name, str(Path.home()))
            folder_p = Path(folder_path)
            if not folder_p.exists():
                return f"[FileManager] Folder not found: {folder_path}"
            items = list(folder_p.iterdir())
            lnk_items = [i for i in items if i.suffix.lower() == ".lnk"]
            if lnk_items:
                names = "\n".join(f"  - {i.stem}" for i in sorted(lnk_items, key=lambda x: x.name.lower()))
                other_count = len(items) - len(lnk_items)
                return (
                    f"[FileManager] Your {folder_name} has {len(lnk_items)} app shortcut(s):\n{names}\n"
                    f"  ({other_count} other file(s) also present)"
                )
            lines = [f"  {'[DIR]' if i.is_dir() else '[FILE]'} {i.name}" for i in sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))[:30]]
            header = f"[FileManager] {folder_name.capitalize()} — {len(items)} item(s):"
            return header + "\n" + "\n".join(lines)
        else:
            return f"[FileManager] Unknown action: {action}"

    # -----------------------------------------------------------------------
    # Action implementations
    # -----------------------------------------------------------------------

    def _action_open(self, target: str) -> str:
        target_clean = target.strip().lower()
        # Look up APP_MAP
        for alias, cmd in APP_MAP.items():
            if alias in target_clean:
                return self.open_app(cmd, alias)
        # Try as a direct path / program
        return self.open_app(target.strip(), target.strip())

    def _action_list(self, folder_hint: str) -> str:
        path = self._resolve_path(folder_hint.lower()) or folder_hint
        return self.list_directory(path)

    def _action_move(self, src_hint: str, dst_hint: str) -> str:
        src = self._resolve_path(src_hint.strip().lower()) or src_hint.strip()
        dst = self._resolve_path(dst_hint.strip().lower()) or dst_hint.strip()
        if not Path(src).exists():
            return f"[FileManager] Source not found: {src}"
        try:
            shutil.move(src, dst)
            return f"[FileManager] Moved: {src}  ->  {dst}"
        except Exception as e:
            return f"[FileManager] Move failed: {e}"

    def _action_copy(self, src_hint: str, dst_hint: str) -> str:
        src = self._resolve_path(src_hint.strip().lower()) or src_hint.strip()
        dst = self._resolve_path(dst_hint.strip().lower()) or dst_hint.strip()
        if not Path(src).exists():
            return f"[FileManager] Source not found: {src}"
        try:
            if Path(src).is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            return f"[FileManager] Copied: {src}  ->  {dst}"
        except Exception as e:
            return f"[FileManager] Copy failed: {e}"

    def _action_find(self, pattern: str, folder_hint: str) -> str:
        folder = self._resolve_path(folder_hint.strip().lower()) or folder_hint.strip()
        folder_path = Path(folder)
        if not folder_path.exists():
            return f"[FileManager] Folder not found: {folder}"

        # Convert natural language to glob: "pdfs" -> "*.pdf"
        glob_pat = self._nl_to_glob(pattern)
        try:
            results = list(folder_path.rglob(glob_pat))[:30]
            if not results:
                return f"[FileManager] No files matching '{glob_pat}' in {folder}"
            lines = [f"  {r.relative_to(folder_path)}" for r in results]
            return f"Found {len(results)} file(s) in {folder}:\n" + "\n".join(lines)
        except Exception as e:
            return f"[FileManager] Find failed: {e}"

    def _action_organize(self, folder_hint: str) -> str:
        folder = self._resolve_path(folder_hint.strip().lower()) or folder_hint.strip()
        folder_path = Path(folder)
        if not folder_path.exists():
            return f"[FileManager] Folder not found: {folder}"

        moved = 0
        skipped = 0
        for item in list(folder_path.iterdir()):
            if item.is_dir():
                continue
            ext = item.suffix.lower()
            category = "other"
            for cat, exts in EXT_CATEGORY.items():
                if ext in exts:
                    category = cat
                    break
            dest_dir = folder_path / category.capitalize()
            dest_dir.mkdir(exist_ok=True)
            try:
                shutil.move(str(item), str(dest_dir / item.name))
                moved += 1
            except Exception:
                skipped += 1

        return (f"[FileManager] Organized {folder}:\n"
                f"  {moved} file(s) sorted into category folders.\n"
                f"  {skipped} file(s) skipped (conflicts).")

    def _action_delete(self, target: str, location_hint: str = "") -> str:
        """
        Find and delete files/shortcuts.
        Supports:
          - Bulk mode: "all shortcuts", "all lnk files", "all app shortcuts"
                       "all [ext] files", "all files"
          - Specific:  "discord", "discord from desktop"
        """
        target_clean = target.strip().lower()

        # Strip leading noise words
        for noise in ("the", "it", "now", "please", "my"):
            target_clean = re.sub(rf"^{noise}\s+", "", target_clean).strip()
            target_clean = re.sub(rf"\s+{noise}\s+", " ", target_clean).strip()

        # Resolve search directories
        search_dirs = []
        if location_hint:
            resolved = self._resolve_path(location_hint.strip().lower())
            if resolved:
                search_dirs.append(Path(resolved))
        if not search_dirs:
            search_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Downloads",
            ]

        # ── Bulk-delete mode ────────────────────────────────────────────
        # Triggered by: "all shortcuts", "all app shortcuts", "all lnk",
        #               "all [ext] files", "all files"
        BULK_SHORTCUTS = {
            "all shortcuts", "all app shortcuts", "all apps", "all app shortcut",
            "all application shortcuts", "all lnk", "all lnk files",
            "all desktop shortcuts",
        }
        bulk_ext = None
        if target_clean in BULK_SHORTCUTS or re.match(r"all\s+(app|application)?\s*shortcuts?", target_clean):
            bulk_ext = ".lnk"
        elif m := re.match(r"all\s+(\w+)\s+files?", target_clean):
            # "all pdf files", "all mp3 files", etc.
            raw_ext = m.group(1).lower()
            bulk_ext = raw_ext if raw_ext.startswith(".") else f".{raw_ext}"
        elif target_clean in ("all files", "everything"):
            bulk_ext = "*"   # delete ALL files (not dirs)

        if bulk_ext is not None:
            found = []
            for d in search_dirs:
                if not d.exists():
                    continue
                for item in d.iterdir():
                    if item.is_dir():
                        continue
                    if bulk_ext == "*" or item.suffix.lower() == bulk_ext:
                        found.append(item)

            if not found:
                loc = ", ".join(str(d) for d in search_dirs)
                ext_desc = "shortcuts (.lnk)" if bulk_ext == ".lnk" else f"{bulk_ext} files"
                return f"[FileManager] No {ext_desc} found in: {loc}"

            deleted, failed = [], []
            for f in found:
                try:
                    f.unlink()
                    deleted.append(f.name)
                except Exception as e:
                    failed.append(f"{f.name}: {e}")

            result = f"[FileManager] Bulk deleted {len(deleted)} file(s):\n"
            result += "\n".join(f"  - {n}" for n in deleted)
            if failed:
                result += f"\n  Errors: {'; '.join(failed)}"
            return result

        # ── Specific name-match mode ─────────────────────────────────────
        found = []
        for d in search_dirs:
            if not d.exists():
                continue
            for item in d.iterdir():
                stem = item.stem.lower()
                if target_clean in stem or stem in target_clean:
                    found.append(item)

        if not found:
            searched = ", ".join(str(d) for d in search_dirs)
            return (
                f"[FileManager] No file/shortcut matching '{target}' found in:\n"
                f"  {searched}\n"
                f"  Tip: 'delete discord from desktop' or 'delete all shortcuts from desktop'"
            )

        deleted = []
        failed  = []
        for f in found:
            try:
                if f.is_dir():
                    shutil.rmtree(str(f))
                else:
                    f.unlink()
                deleted.append(f.name)
            except Exception as e:
                failed.append(f"{f.name}: {e}")

        result = f"[FileManager] Deleted: {', '.join(deleted)}"
        if failed:
            result += f"\n  Errors: {'; '.join(failed)}"
        return result

    def _action_system_health(self) -> str:
        return self.system_health()

    def _action_profile(self, profile_name: str) -> str:
        # Import here to avoid circular dependency
        from core.profiles.profiles import ProfileManager
        pm = ProfileManager(self)
        return pm.run(profile_name)

    # -----------------------------------------------------------------------
    # File write (used by Phase 4 chains)
    # -----------------------------------------------------------------------

    def write_file(self, path: str, content: str) -> str:
        """
        Write text content to an absolute file path.
        Creates parent directories if they don't exist.
        Used by HelixChainRunner to persist research output.
        Returns a short status string.
        """
        try:
            dest = Path(path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            size_kb = dest.stat().st_size / 1024
            return f"[FileManager] Written: {dest.name}  ({size_kb:.1f} KB)"
        except Exception as e:
            return f"[FileManager] Write failed: {e}"

    # -----------------------------------------------------------------------
    # System health
    # -----------------------------------------------------------------------

    def system_health(self) -> str:
        cpu     = psutil.cpu_percent(interval=0.5)
        ram     = psutil.virtual_memory()
        battery = psutil.sensors_battery()

        lines = [
            "[HELIX] System Health Report",
            "-" * 40,
            f"  CPU   : {cpu:.1f}%  ({psutil.cpu_count()} cores, {psutil.cpu_count(logical=False)} physical)",
            f"  RAM   : {ram.used / 1e9:.1f} GB / {ram.total / 1e9:.1f} GB  ({ram.percent:.0f}% used)",
        ]

        # All drives
        lines.append("  Drives:")
        total_all = 0
        used_all  = 0
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_all += usage.total
                used_all  += usage.used
                lines.append(
                    f"    {part.mountpoint:<5} {usage.used/1e9:>6.1f} / {usage.total/1e9:>6.1f} GB  "
                    f"({usage.percent:.0f}% used)"
                )
            except PermissionError:
                pass
        lines.append(
            f"  Total : {used_all/1e9:.1f} / {total_all/1e9:.1f} GB across all drives"
        )

        if battery:
            charge = f"{battery.percent:.0f}%"
            status = "charging" if battery.power_plugged else "on battery"
            lines.append(f"  Power : {charge}  ({status})")
        else:
            lines.append("  Power : No battery (desktop)")

        # Top 5 CPU consumers
        procs = sorted(
            psutil.process_iter(["name", "cpu_percent"]),
            key=lambda p: p.info["cpu_percent"] or 0,
            reverse=True
        )[:5]
        lines.append("  Top processes:")
        for p in procs:
            lines.append(f"    {p.info['name'][:22]:<24} {p.info['cpu_percent']:.1f}%")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def open_app(self, app_cmd: str, label: str = None) -> str:
        label = label or app_cmd
        try:
            subprocess.Popen(app_cmd, shell=True)
            return f"[FileManager] Launched: {label}"
        except Exception as e:
            return f"[FileManager] Failed to launch {label}: {e}"

    def list_directory(self, path: str) -> str:
        try:
            items = sorted(Path(path).iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            lines = [f"  {'[DIR] ' if i.is_dir() else '[FILE]'} {i.name}" for i in items[:30]]
            header = f"\nContents of {path}  ({min(len(items),30)} of {len(items)} items):"
            return header + "\n" + "\n".join(lines)
        except Exception as e:
            return f"[FileManager] Cannot list {path}: {e}"

    def move_file(self, src: str, dst: str) -> str:
        shutil.move(src, dst)
        return f"Moved: {src} -> {dst}"

    def _resolve_path(self, text: str) -> str:
        """
        Resolve common folder names + absolute paths from free text.
        Returns resolved absolute path string or None.
        """
        text = text.strip().lower()
        # Named shortcuts
        for name, resolved in COMMON_DIRS.items():
            if name in text:
                return resolved
        # Absolute path in original text
        m = re.search(r'[A-Za-z]:\\[^\s"\']+|/[^\s"\']+', text)
        if m:
            return m.group(0)
        return None

    def _nl_to_glob(self, natural: str) -> str:
        """Convert natural language like 'pdfs' or '*.py' to glob pattern."""
        natural = natural.strip().lower()
        # Already a glob
        if "*" in natural or "?" in natural:
            return natural
        # Common aliases
        aliases = {
            "pdf": "*.pdf", "pdfs": "*.pdf",
            "python": "*.py", "py": "*.py", "python files": "*.py",
            "image": "*.jpg", "images": "*.{jpg,png,gif}",
            "word": "*.docx", "excel": "*.xlsx",
            "text": "*.txt", "txt": "*.txt",
            "video": "*.mp4", "videos": "*.mp4",
            "zip": "*.zip", "zips": "*.zip",
            "csv": "*.csv", "json": "*.json",
        }
        if natural in aliases:
            return aliases[natural]
        # Treat as extension
        if not natural.startswith("."):
            natural = "." + natural
        return f"*{natural}"


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

class HelixWatcher(FileSystemEventHandler):
    """
    Passive filesystem monitor.
    Calls callback with a human-readable string on file creation/move.
    """
    def __init__(self, callback=None):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and self.callback:
            fname = Path(event.src_path).name
            self.callback(f"New file detected in {Path(event.src_path).parent.name}: {fname}")

    def on_moved(self, event):
        if self.callback:
            self.callback(f"File moved: {Path(event.src_path).name} -> {Path(event.dest_path).name}")


def start_watcher(path: str, callback=None) -> Observer:
    observer = Observer()
    observer.schedule(HelixWatcher(callback), path, recursive=False)
    observer.start()
    print(f"[Watcher] Monitoring: {path}")
    return observer
