"""
HELIX -- Cloud Command Parser (Phase 4 Enhancement)
Uses Cloud Oracle to interpret complex natural language OS commands
that FileManager's fast-path patterns can't handle.

Instead of hardcoding every possible phrasing, we ask the cloud AI:
  "Parse this OS command into a structured JSON action"

The AI returns something like:
  {"action": "delete", "bulk": true, "extension": ".lnk", "location": "desktop"}

Then HELIX executes it deterministically via FileManager.

Privacy: The prompt is PII-sanitized by Sentinel before reaching this module.
         No personal data ever leaves the machine unredacted.
"""
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


# ---------------------------------------------------------------------------
# System prompt — tells the cloud AI exactly what JSON schema to return
# ---------------------------------------------------------------------------
_PARSE_SYSTEM_PROMPT = """\
You are HELIX's OS command interpreter for Windows. Parse the user's natural \
language command into a JSON action object.

Available actions and their JSON schemas:

1. delete  — delete files/shortcuts
   {{"action":"delete","bulk":true|false,"target":"filename or null","extension":".lnk|.pdf|*|null","location":"desktop|downloads|documents|null"}}

2. move    — move a file from one place to another
   {{"action":"move","source":"filename","source_location":"desktop|downloads|...","destination":"desktop|downloads|documents|..."}}

3. copy    — copy a file
   {{"action":"copy","source":"filename","source_location":"...","destination":"..."}}

4. find    — find files matching a pattern
   {{"action":"find","pattern":"*.pdf or filename","location":"downloads|desktop|..."}}

5. list    — list contents of a folder
   {{"action":"list","location":"desktop|downloads|documents|..."}}

6. open    — launch an application
   {{"action":"open","app":"vscode|chrome|spotify|discord|notepad|..."}}

7. create  — create a new file with content
   {{"action":"create","filename":"name.ext","location":"desktop|documents|...","content":"full file content as a string"}}

8. unknown — cannot be parsed as a local OS command (it's a knowledge question)
   {{"action":"unknown","reason":"brief explanation"}}

Rules:
- Return ONLY the JSON object, no markdown, no explanation
- "bulk":true means operate on ALL matching files, not just one
- extension null means match by filename, not extension
- location null means search Desktop then Downloads (default)
- For "create" with html/txt/py files, generate the FULL file content in the "content" field
- If the command is clearly a knowledge/cloud question, return {{"action":"unknown"}}

Examples:
"delete all app shortcuts from desktop" -> {{"action":"delete","bulk":true,"target":null,"extension":".lnk","location":"desktop"}}
"delete all pdf files from downloads"   -> {{"action":"delete","bulk":true,"target":null,"extension":".pdf","location":"downloads"}}
"remove discord from desktop"           -> {{"action":"delete","bulk":false,"target":"discord","extension":null,"location":"desktop"}}
"move notes.txt to documents"           -> {{"action":"move","source":"notes.txt","source_location":"desktop","destination":"documents"}}
"find all excel files in documents"     -> {{"action":"find","pattern":"*.xlsx","location":"documents"}}
"open spotify"                          -> {{"action":"open","app":"spotify"}}
"make a html file that says hello"      -> {{"action":"create","filename":"hello.html","location":"desktop","content":"<!DOCTYPE html><html><body><h1>hello</h1></body></html>"}}
"explain machine learning"              -> {{"action":"unknown","reason":"knowledge question"}}

Command to parse: {prompt}
"""


class CloudCommandParser:
    """
    Sends unrecognised local OS commands to the Cloud Oracle for NLP parsing.
    Returns a structured dict that FileManager can execute directly.
    """

    def __init__(self, oracle):
        self.oracle = oracle

    def parse(self, prompt: str) -> dict:
        """
        Ask the cloud AI to parse the prompt into a structured action dict.
        Returns a dict with 'action' key, or {'action': 'unknown'} on failure.
        """
        cloud_prompt = _PARSE_SYSTEM_PROMPT.format(prompt=prompt)

        try:
            raw = self.oracle.query(cloud_prompt)
        except Exception as e:
            return {"action": "unknown", "reason": f"Cloud unavailable: {e}"}

        # Strip any markdown code fences the model might add
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict) or "action" not in parsed:
                return {"action": "unknown", "reason": "Invalid response format"}
            return parsed
        except json.JSONDecodeError:
            # Try to extract JSON from within the response
            m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    pass
            return {"action": "unknown", "reason": f"Could not parse: {raw[:100]}"}

    def execute_parsed(self, parsed: dict, file_manager) -> str:
        """
        Execute a parsed action dict using FileManager methods.
        Returns a response string.
        """
        action = parsed.get("action", "unknown")

        if action == "delete":
            location   = parsed.get("location") or ""
            target     = parsed.get("target") or ""
            extension  = parsed.get("extension") or ""
            bulk       = parsed.get("bulk", False)

            if bulk:
                # Construct a bulk-delete target string that _action_delete understands
                if extension and extension != "*":
                    ext_clean = extension.lstrip(".")
                    synthetic_target = f"all {ext_clean} files"
                elif extension == "*":
                    synthetic_target = "all files"
                elif "shortcut" in parsed.get("reason", "").lower():
                    synthetic_target = "all shortcuts"
                else:
                    synthetic_target = target or "all files"
            else:
                synthetic_target = target

            return file_manager._action_delete(synthetic_target, location)

        elif action == "move":
            src      = parsed.get("source", "")
            src_loc  = parsed.get("source_location", "desktop")
            dst      = parsed.get("destination", "")
            return file_manager._action_move(
                f"{src_loc}/{src}" if src else src_loc, dst
            )

        elif action == "copy":
            src     = parsed.get("source", "")
            src_loc = parsed.get("source_location", "desktop")
            dst     = parsed.get("destination", "")
            return file_manager._action_copy(
                f"{src_loc}/{src}" if src else src_loc, dst
            )

        elif action == "find":
            pattern  = parsed.get("pattern", "*")
            location = parsed.get("location", "downloads")
            return file_manager._action_find(pattern, location)

        elif action == "list":
            location = parsed.get("location", "desktop")
            return file_manager._action_list(location)

        elif action == "open":
            app = parsed.get("app", "")
            return file_manager._action_open(app)

        elif action == "create":
            filename = parsed.get("filename", "helix_output.txt")
            location = parsed.get("location", "documents")
            content  = parsed.get("content", "")
            from pathlib import Path
            resolved = file_manager._resolve_path(location) or str(Path.home() / "Documents")
            import os
            filepath = os.path.join(resolved, filename)
            return file_manager.write_file(filepath, content or "")

        elif action == "unknown":
            reason = parsed.get("reason", "")
            return f"__STILL_UNKNOWN__:{reason}"

        else:
            return f"[CloudParser] Unrecognised action type: {action}"
