"""
HELIX -- Email Drafter (Phase 4)
Privacy-safe Gmail drafting pipeline.

Flow:
  1. Sentinel redacts any PII from the user's email request
  2. Cloud Oracle drafts a professional email body
  3. HELIX shows the draft to the user for review
  4. On approval → opens Gmail compose URL pre-filled with the body
     (email never auto-sent -- user always reviews + sends manually)

Privacy guarantee:
  - The professor's name / recipient's email is NEVER sent to the cloud
  - Only the topic/context (already PII-stripped by Sentinel) leaves the machine
"""
import sys
import os
import re
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from config.settings import GMAIL_COMPOSE_URL


# ---------------------------------------------------------------------------
# Email subject extractor (regex, no LLM)
# ---------------------------------------------------------------------------
_SUBJECT_PATTERNS = [
    re.compile(r"about\s+(.+?)(?:\s+to\s+|\s+for\s+|$)", re.I),
    re.compile(r"regarding\s+(.+?)(?:\s+to\s+|\s+for\s+|$)", re.I),
    re.compile(r"for\s+(.+?)(?:\s+to\s+|$)", re.I),
]

_DRAFT_SYSTEM_PROMPT = """\
You are a professional email writing assistant.
Write ONLY the email body (no subject line, no "To:" field, no headers).
Keep it polite, professional, and concise (3-5 sentences max).
Do not include any names — use "[Recipient]" and "[Your name]" as placeholders.
Topic: {topic}
"""


def extract_email_topic(sanitized_prompt: str) -> str:
    """
    Extract the email topic from the sanitized prompt.
    e.g. "draft an email about assignment extension" → "assignment extension"
    """
    pl = sanitized_prompt.lower().strip()

    # Strip common prefix phrases
    for prefix in [
        "draft an email about", "draft an email regarding", "draft email about",
        "draft email regarding", "write an email about", "write email about",
        "compose an email about", "compose email about",
        "draft an email for", "write an email for",
    ]:
        if pl.startswith(prefix):
            return sanitized_prompt[len(prefix):].strip()

    # Try subject patterns
    for pat in _SUBJECT_PATTERNS:
        m = pat.search(sanitized_prompt)
        if m:
            return m.group(1).strip()

    # Fallback: return everything after "email"
    idx = pl.find("email")
    if idx != -1:
        return sanitized_prompt[idx + 5:].strip()

    return sanitized_prompt.strip()


class EmailDrafter:
    """
    Privacy-safe email drafting module.
    Requires a CloudOracle instance and a SentinelNode instance.
    """

    def __init__(self, oracle, sentinel):
        self.oracle   = oracle
        self.sentinel = sentinel

    def draft(self, raw_prompt: str) -> dict:
        """
        Full drafting pipeline.

        Returns a dict:
          {
            'topic':      str,   # extracted topic
            'draft':      str,   # drafted email body
            'gmail_url':  str,   # pre-filled Gmail compose URL
            'ready':      bool,  # True if draft was successfully generated
          }
        """
        # Step 1 — PII redact the user's request
        redacted = self.sentinel.redact_pii(raw_prompt)

        # Step 2 — Extract topic from the redacted prompt
        topic = extract_email_topic(redacted)
        if not topic:
            topic = "the requested topic"

        # Step 3 — Cloud drafts the body
        cloud_prompt = _DRAFT_SYSTEM_PROMPT.format(topic=topic)
        draft_body = self.oracle.query(cloud_prompt)

        # Step 4 — Build Gmail compose URL
        encoded_body = urllib.parse.quote(draft_body)
        encoded_subject = urllib.parse.quote(f"RE: {topic.title()}")
        gmail_url = GMAIL_COMPOSE_URL.format(
            body=encoded_body,
            subject=encoded_subject,
        )

        return {
            "topic":     topic,
            "draft":     draft_body,
            "gmail_url": gmail_url,
            "ready":     not draft_body.startswith("[Oracle]"),
        }

    def open_gmail(self, gmail_url: str) -> str:
        """Open Gmail compose in the default browser."""
        try:
            webbrowser.open(gmail_url)
            return "[EmailDrafter] Gmail compose opened in browser. Review and send manually."
        except Exception as e:
            return f"[EmailDrafter] Could not open browser: {e}"
