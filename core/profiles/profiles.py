"""
HELIX -- Workflow Profiles (Phase 3)
Trigger phrases like "code mode" launch a full sequence of OS actions.
Profiles are pure FileManager calls -- no LLM, no cloud, instant execution.
"""
from pathlib import Path


# ---------------------------------------------------------------------------
# Profile definitions
# Each action is a dict: {type, ...params}
# ---------------------------------------------------------------------------
WORKFLOW_PROFILES = {
    "code mode": {
        "description": "Developer workspace: VS Code + Spotify + GitHub in browser",
        "actions": [
            {"type": "open",     "target": "code"},
            {"type": "open",     "target": "spotify"},
            {"type": "open_url", "url":    "https://github.com"},
            {"type": "open_url", "url":    "https://docs.python.org/3/"},
        ],
    },
    "study mode": {
        "description": "Study workspace: browser + list notes folder",
        "actions": [
            {"type": "open",     "target": "chrome"},
            {"type": "open_url", "url":    "https://calendar.google.com"},
            {"type": "list",     "folder": str(Path.home() / "Documents")},
        ],
    },
    "presentation mode": {
        "description": "Presentation: PowerPoint + file explorer on Desktop",
        "actions": [
            {"type": "open",  "target": "powerpnt"},
            {"type": "open",  "target": "explorer"},
            {"type": "list",  "folder": str(Path.home() / "Desktop")},
        ],
    },
    "focus mode": {
        "description": "Deep focus: close distractions, open notes",
        "actions": [
            {"type": "open",     "target": "notepad"},
            {"type": "open_url", "url":    "https://pomofocus.io"},
        ],
    },
}


class ProfileManager:

    def __init__(self, file_manager):
        self.fm = file_manager

    def run(self, profile_name: str) -> str:
        name = profile_name.strip().lower()
        profile = WORKFLOW_PROFILES.get(name)
        if profile is None:
            available = ", ".join(WORKFLOW_PROFILES.keys())
            return f"[Profiles] Unknown profile '{name}'. Available: {available}"

        results = [f"[HELIX] Activating '{name}' -- {profile['description']}"]
        for step in profile["actions"]:
            action_type = step["type"]
            if action_type == "open":
                result = self.fm.open_app(step["target"], step["target"])
                results.append(f"  + {result}")
            elif action_type == "open_url":
                import webbrowser
                webbrowser.open(step["url"])
                results.append(f"  + Opened: {step['url']}")
            elif action_type == "list":
                results.append(self.fm.list_directory(step["folder"]))
            else:
                results.append(f"  ? Unknown step type: {action_type}")

        results.append(f"[Profiles] '{name}' activated successfully.")
        return "\n".join(results)

    def list_profiles(self) -> str:
        lines = ["[HELIX] Available Workflow Profiles:", "-" * 36]
        for name, p in WORKFLOW_PROFILES.items():
            lines.append(f"  '{name}' -- {p['description']}")
        return "\n".join(lines)
