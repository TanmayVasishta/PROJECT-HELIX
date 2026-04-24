"""
HELIX -- Router (Phase 4)
Full pipeline with:
  - Regex fast-path (0ms for obvious commands, no LLM)
  - Multi-step chain detection (0ms, Phase 4: research+save, email draft)
  - Sentinel intent classification + PII redaction (LLM, ~15s on CPU)
  - Cloud Oracle with local fallback
  - Workflow profile detection
  - Structured audit log (every event recorded)
  - Human-in-the-Loop gate for destructive actions
"""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.sentinel.node       import SentinelNode
from core.oracle.cloud        import CloudOracle
from core.oracle.command_parser import CloudCommandParser
from core.middleware.file_manager import FileManager
from core.memory.memory       import HelixMemory
from core.logging.audit_log   import HelixAuditLog


# Commands that show audit log instead of going through normal pipeline
AUDIT_COMMANDS = {"audit log", "show audit", "what did i do", "helix log", "show log"}
STATS_COMMANDS = {"audit stats", "log stats", "helix stats"}


class HelixRouter:
    def __init__(self):
        print("[HELIX] Initializing subsystems...")
        self.sentinel       = SentinelNode()
        self.oracle         = CloudOracle()
        self.cmd_parser     = CloudCommandParser(self.oracle)  # parses NL OS cmds → JSON → local exec
        self.file_manager   = FileManager()
        self.memory         = HelixMemory()
        self.audit          = HelixAuditLog()
        # Phase 4 -- chain runner (lazy-instantiated on first use)
        self._chain_runner  = None
        print("[HELIX] All systems online.\n")

    def process(self, user_prompt: str, confirm_callback=None) -> str:
        """
        Full HELIX pipeline:
        0.  Special command shortcuts (audit log, stats)
        0.5 [Phase 4] Multi-step chain detection (regex, 0ms)
        1.  Regex fast-path -- instant, no LLM
        2.  Memory context retrieval
        3.  Sentinel: classify intent + PII redaction
        4.  Route: local -> FileManager | cloud -> Oracle
        5.  Human-in-the-Loop for destructive actions
        6.  Audit log every event
        """
        t_start = time.monotonic()
        prompt_lower = user_prompt.strip().lower()

        # ----------------------------------------------------------------
        # Step 0 -- special meta-commands (no LLM, no audit write needed)
        # ----------------------------------------------------------------
        if prompt_lower in AUDIT_COMMANDS:
            return self.audit.query_log(n=15)
        if prompt_lower in STATS_COMMANDS:
            return self.audit.summary_stats()

        print(f"[Router] Input: '{user_prompt}'")

        # ----------------------------------------------------------------
        # Step 0.5 -- Phase 4: Multi-step chain detection (0ms, no LLM)
        # ----------------------------------------------------------------
        from core.chains.multi_step import HelixChainRunner
        chain_name, chain_groups = HelixChainRunner.detect(user_prompt)
        if chain_name:
            print(f"[Router] Chain detected: '{chain_name}' -> running multi-step pipeline")
            runner = self._get_chain_runner()
            return runner.run(chain_name, chain_groups, user_prompt, confirm_callback)

        # ----------------------------------------------------------------
        # Step 1 -- Regex fast-path (0ms, bypasses LLM entirely)
        # ----------------------------------------------------------------
        action_tag, groups = self.file_manager.fast_path_match(user_prompt)
        if action_tag:
            print(f"[Router] Fast-path match: {action_tag} -> executing instantly")

            # Destructive gate still applies on fast-path
            if self.file_manager.is_destructive(user_prompt):
                confirmed = self._confirm_destructive(user_prompt, confirm_callback)
                if not confirmed:
                    response = "[HELIX] Action cancelled by user."
                    self._log(user_prompt, "local", False, "fast_path", action_tag,
                              t_start, "cancelled")
                    return response

            response = self.file_manager.execute(
                user_prompt, action_tag=action_tag, groups=groups
            )
            self.memory.store(user_prompt, response)
            self._log(user_prompt, "local", False, "fast_path", action_tag, t_start, "ok")
            return response

        # ----------------------------------------------------------------
        # Step 2 -- Memory context
        # ----------------------------------------------------------------
        context = self.memory.retrieve(user_prompt)
        if context:
            print(f"[Router] Memory context loaded ({len(context)} chars)")

        # ----------------------------------------------------------------
        # Step 3 -- Sentinel: classify + PII redact
        # ----------------------------------------------------------------
        result    = self.sentinel.classify_intent(user_prompt)
        intent    = result["intent"]
        sanitized = result["sanitized_prompt"]
        pii       = result["pii_detected"]
        print(f"[Router] Intent: {intent.upper()} | PII scrubbed: {pii}")

        # ----------------------------------------------------------------
        # Step 4 -- Route
        # ----------------------------------------------------------------
        routed_to = "sentinel" if intent == "local" else "oracle"

        if intent == "local":
            if self.file_manager.is_destructive(user_prompt):
                confirmed = self._confirm_destructive(user_prompt, confirm_callback)
                if not confirmed:
                    response = "[HELIX] Action cancelled by user."
                    self.memory.store(user_prompt, response)
                    self._log(user_prompt, intent, pii, routed_to, "cancelled_destructive",
                              t_start, "cancelled")
                    return response

            response = self.file_manager.execute(user_prompt)

            # FileManager couldn't handle it with its deterministic rules.
            # Use CloudCommandParser: cloud parses the intent into structured JSON,
            # then FileManager executes it locally. The cloud never answers for us.
            if response == "__ESCALATE_TO_CLOUD__":
                print("[Router] FileManager needs NL parsing — using CloudCommandParser...")
                parsed   = self.cmd_parser.parse(sanitized)
                action   = parsed.get("action", "unknown")
                print(f"[Router] Parsed action: {action}")
                response = self.cmd_parser.execute_parsed(parsed, self.file_manager)
                routed_to = "cmd_parser"

                # If even the parser couldn't map it (genuinely ambiguous OS command),
                # give a clean error — don't dump it on cloud Oracle for a knowledge answer.
                if response.startswith("__STILL_UNKNOWN__"):
                    reason = response.split(":", 1)[-1].strip()
                    response = (
                        f"[HELIX] I understood this as a local OS task but couldn't map it "
                        f"to an action.\n"
                        f"  Reason: {reason}\n"
                        f"  Try: 'list desktop', 'find pdfs in downloads', 'open chrome'"
                    )
                    routed_to = "unhandled_local"

        else:
            # CLOUD intent: knowledge, reasoning, coding — goes to Oracle
            print("[Router] Forwarding sanitized prompt to Cloud Oracle...")
            response = self.oracle.query(sanitized)

            # If all cloud providers failed, fall back to local Sentinel
            if response.startswith("[Oracle]"):
                print("[Router] Cloud unavailable -- falling back to Sentinel...")
                fallback_prompt = (
                    f"Answer this as best you can using your own knowledge: {sanitized}"
                )
                response  = f"[Local fallback]\n{self.sentinel.llm_raw(fallback_prompt)}"
                routed_to = "fallback"

        # ----------------------------------------------------------------
        # Step 5 -- Store memory + audit
        # ----------------------------------------------------------------
        self.memory.store(user_prompt, response)
        self._log(user_prompt, intent, pii, routed_to, intent + "_response", t_start, "ok")
        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confirm_destructive(self, prompt: str, confirm_callback) -> bool:
        if confirm_callback:
            return confirm_callback(prompt)
        ans = input(
            f"\n  [!] Destructive action detected:\n"
            f"  '{prompt}'\n  Proceed? (y/n): "
        ).strip().lower()
        return ans == "y"

    def _log(self, prompt, intent, pii, routed_to, action, t_start, outcome, err=None):
        self.audit.log_event(
            raw_prompt   = prompt,
            intent       = intent,
            pii_detected = pii,
            routed_to    = routed_to,
            action       = action,
            duration_ms  = (time.monotonic() - t_start) * 1000,
            outcome      = outcome,
            error_msg    = err,
        )

    def _get_chain_runner(self):
        """Lazy-initialize HelixChainRunner on first chain use."""
        if self._chain_runner is None:
            from core.chains.multi_step import HelixChainRunner
            self._chain_runner = HelixChainRunner(
                oracle       = self.oracle,
                sentinel     = self.sentinel,
                file_manager = self.file_manager,
                memory       = self.memory,
                audit        = self.audit,
            )
            print("[Router] Chain runner initialized.")
        return self._chain_runner
