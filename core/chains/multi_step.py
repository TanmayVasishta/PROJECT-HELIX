"""
HELIX -- Multi-Step Chain Runner (Phase 4)
LangChain-style sequential task automation without heavy LangChain imports.

Detects multi-step intent patterns via regex (0ms, no LLM) and executes
a two-step pipeline:
  Step 1: Cloud research / generation  (CloudOracle)
  Step 2: Local file write             (FileManager.write_file)

Supported chain triggers:
  "research X and save [to Y]"
  "summarize X and save [to Y]"
  "write a report on X"
  "find information about X and save"
  "look up X and save it"
  "draft an email about X"   → routed to EmailDrafter

All chains:
  - Use only PII-sanitized prompts for cloud steps
  - Write outputs to CHAIN_OUTPUT_DIR (configurable in settings.py)
  - Log every step to HelixAuditLog
  - Store result in HelixMemory (ChromaDB)
"""
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import CHAIN_OUTPUT_DIR, CHAIN_MAX_TOKENS


# ---------------------------------------------------------------------------
# Chain trigger patterns -- pure regex, evaluated BEFORE Sentinel
# ---------------------------------------------------------------------------
CHAIN_PATTERNS = [
    # research X and save [to/in folder]
    (re.compile(
        r"^(?:research|look\s+up|find\s+(?:info(?:rmation)?\s+)?(?:about|on))\s+(.+?)"
        r"(?:\s+and\s+save(?:\s+(?:it\s+)?(?:to|in)\s+(.+))?)?$",
        re.I
    ), "research_and_save"),

    # summarize X and save
    (re.compile(
        r"^(?:summarize|give\s+me\s+a\s+summary\s+of)\s+(.+?)"
        r"(?:\s+and\s+save(?:\s+(?:it\s+)?(?:to|in)\s+(.+))?)?$",
        re.I
    ), "research_and_save"),

    # write a report on X
    (re.compile(
        r"^(?:write|create|generate)\s+(?:a\s+)?(?:report|summary|notes?|document)\s+"
        r"(?:on|about|for)\s+(.+)$",
        re.I
    ), "research_and_save"),

    # draft an email about X
    (re.compile(
        r"^(?:draft|write|compose)\s+(?:an?\s+)?email\s+"
        r"(?:about|regarding|for|on)\s+(.+)$",
        re.I
    ), "draft_email"),
]

# ---------------------------------------------------------------------------
# Research prompt template (sent to cloud after PII redaction)
# ---------------------------------------------------------------------------
_RESEARCH_PROMPT = """\
You are a knowledgeable research assistant. Provide a clear, well-structured summary.

Topic: {topic}

Instructions:
- Write 3-5 paragraphs covering the key concepts
- Use plain language, avoid excessive jargon
- Include practical applications or examples where relevant
- End with a brief "Key Takeaways" bullet list (3-5 points)

Keep response under {max_tokens} tokens.
"""


def _safe_filename(topic: str) -> str:
    """Convert a topic string to a safe filename."""
    safe = re.sub(r"[^\w\s-]", "", topic.lower())
    safe = re.sub(r"[\s-]+", "_", safe).strip("_")
    date = datetime.now().strftime("%Y%m%d")
    return f"{safe[:40]}_{date}.txt"


class HelixChainRunner:
    """
    Multi-step chain executor for Phase 4.
    Requires oracle, sentinel, file_manager, memory, audit instances.
    """

    def __init__(self, oracle, sentinel, file_manager, memory, audit):
        self.oracle       = oracle
        self.sentinel     = sentinel
        self.fm           = file_manager
        self.memory       = memory
        self.audit        = audit
        # Ensure output directory exists
        Path(CHAIN_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Detection (called from Router at Step 0.5 -- 0ms)
    # -----------------------------------------------------------------------

    @staticmethod
    def detect(prompt: str) -> tuple:
        """
        Check if prompt matches a chain pattern.
        Returns (chain_name, regex_groups) or (None, None).
        Called BEFORE Sentinel -- pure regex, 0ms.
        """
        for pattern, chain_name in CHAIN_PATTERNS:
            m = pattern.match(prompt.strip())
            if m:
                return chain_name, m.groups()
        return None, None

    # -----------------------------------------------------------------------
    # Chain dispatcher
    # -----------------------------------------------------------------------

    def run(self, chain_name: str, groups: tuple, raw_prompt: str,
            confirm_callback=None) -> str:
        """
        Execute the named chain and return the final response string.
        """
        t_start = time.monotonic()

        if chain_name == "research_and_save":
            result = self._chain_research_and_save(groups, raw_prompt)
        elif chain_name == "draft_email":
            result = self._chain_draft_email(raw_prompt, confirm_callback)
        else:
            result = f"[Chain] Unknown chain: {chain_name}"

        # Always store + audit
        self.memory.store(raw_prompt, result, metadata={"type": "chain", "chain": chain_name})
        duration_ms = (time.monotonic() - t_start) * 1000
        self.audit.log_event(
            raw_prompt   = raw_prompt,
            intent       = "chain",
            pii_detected = False,
            routed_to    = f"chain:{chain_name}",
            action       = chain_name,
            duration_ms  = duration_ms,
            outcome      = "ok" if not result.startswith("[Chain] Error") else "error",
        )
        return result

    # -----------------------------------------------------------------------
    # Chain: Research + Save
    # -----------------------------------------------------------------------

    def _chain_research_and_save(self, groups: tuple, raw_prompt: str) -> str:
        """
        Step 1: Redact PII from topic
        Step 2: Cloud research
        Step 3: Write to file
        """
        # Extract topic from regex groups
        topic = (groups[0] or "").strip() if groups else ""
        save_folder_hint = (groups[1] or "").strip() if len(groups) > 1 else ""

        if not topic:
            # Fallback: use whole prompt as topic
            topic = raw_prompt

        # Step 1 — PII redact the topic
        print(f"[Chain] Step 1/3 — Redacting PII from topic: '{topic}'")
        sanitized_topic = self.sentinel.redact_pii(topic)

        # Step 2 — Cloud research
        print(f"[Chain] Step 2/3 — Researching '{sanitized_topic}' via cloud...")
        cloud_prompt = _RESEARCH_PROMPT.format(
            topic=sanitized_topic,
            max_tokens=CHAIN_MAX_TOKENS,
        )
        research_result = self.oracle.query(cloud_prompt)

        if research_result.startswith("[Oracle]"):
            return (
                f"[Chain] Research failed — cloud unavailable.\n{research_result}"
            )

        # Step 3 — Write to file
        print(f"[Chain] Step 3/3 — Saving research to disk...")

        # Resolve save folder
        if save_folder_hint:
            save_dir = self.fm._resolve_path(save_folder_hint) or CHAIN_OUTPUT_DIR
        else:
            save_dir = CHAIN_OUTPUT_DIR

        filename = _safe_filename(sanitized_topic)
        filepath = Path(save_dir) / filename

        # Build file content
        header = (
            f"HELIX Research Output\n"
            f"{'=' * 50}\n"
            f"Topic     : {sanitized_topic}\n"
            f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Source    : HELIX Cloud Oracle (PII-safe)\n"
            f"{'=' * 50}\n\n"
        )
        write_result = self.fm.write_file(str(filepath), header + research_result)

        return (
            f"[Chain] Research + Save complete!\n"
            f"  Topic   : {sanitized_topic}\n"
            f"  Saved to: {filepath}\n"
            f"  {write_result}\n\n"
            f"--- Preview (first 300 chars) ---\n"
            f"{research_result[:300]}..."
        )

    # -----------------------------------------------------------------------
    # Chain: Draft Email
    # -----------------------------------------------------------------------

    def _chain_draft_email(self, raw_prompt: str, confirm_callback=None) -> str:
        """
        Step 1: Sentinel redacts PII
        Step 2: Cloud drafts email body
        Step 3: Show draft to user
        Step 4: On approval → open Gmail compose URL
        """
        from core.chains.email_drafter import EmailDrafter

        print("[Chain] Step 1/3 — Redacting PII from email request...")
        drafter = EmailDrafter(self.oracle, self.sentinel)

        print("[Chain] Step 2/3 — Cloud drafting email body...")
        result = drafter.draft(raw_prompt)

        if not result["ready"]:
            return (
                f"[Chain] Email draft failed — cloud unavailable.\n"
                f"Cloud response: {result['draft']}"
            )

        # Step 3 — Show draft to user
        output_lines = [
            f"[Chain] Email Draft Ready!",
            f"  Topic: {result['topic']}",
            f"",
            f"--- Draft Body ---",
            result["draft"],
            f"------------------",
            f"",
        ]

        # Step 4 — Ask to open Gmail
        if confirm_callback:
            open_gmail = confirm_callback(
                "Open Gmail compose with this draft pre-filled? (y/n)"
            )
        else:
            try:
                ans = input(
                    "\n[Chain] Open Gmail compose with this draft? (y/n): "
                ).strip().lower()
                open_gmail = ans == "y"
            except (EOFError, KeyboardInterrupt):
                open_gmail = False

        if open_gmail:
            print("[Chain] Step 3/3 — Opening Gmail compose...")
            gmail_result = drafter.open_gmail(result["gmail_url"])
            output_lines.append(gmail_result)
        else:
            output_lines.append(
                "[Chain] Gmail not opened. Copy the draft above and paste it manually."
            )

        return "\n".join(output_lines)
