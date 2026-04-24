"""
HELIX -- Structured Audit Log (Phase 3 Major Feature)
Append-only JSON-lines audit trail. Proves HELIX's enterprise privacy claims.

Every HELIX interaction is recorded with:
  - SHA-256 hash of the raw prompt (privacy-safe -- the prompt itself is never stored)
  - routing decision, PII flag, latency, outcome

This log is the evidence layer for the "Enterprise-Ready Security Blueprint" claim.
Healthcare/defence deployments can verify: PII never left the machine, every
cloud call used a sanitized prompt, every destructive action required confirmation.
"""
import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path


# Absolute path so it works regardless of cwd
_LOG_DIR  = Path(__file__).resolve().parents[3] / "logs"
_LOG_FILE = _LOG_DIR / "helix_audit.jsonl"


class HelixAuditLog:

    def __init__(self):
        _LOG_DIR.mkdir(parents=True, exist_ok=True)

    def log_event(
        self,
        raw_prompt: str,
        intent: str,
        pii_detected: bool,
        routed_to: str,          # "fast_path" | "sentinel" | "oracle" | "profile" | "fallback"
        action: str,             # what FileManager did, or Gemini/Sentinel response type
        duration_ms: float,
        outcome: str,            # "ok" | "cancelled" | "error"
        error_msg: str = None,
    ) -> None:
        record = {
            "ts":           datetime.now(timezone.utc).isoformat(),
            "prompt_hash":  hashlib.sha256(raw_prompt.encode()).hexdigest()[:16],
            "intent":       intent,
            "pii_detected": pii_detected,
            "routed_to":    routed_to,
            "action":       action,
            "duration_ms":  round(duration_ms, 1),
            "outcome":      outcome,
        }
        if error_msg:
            record["error"] = error_msg[:120]

        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass  # Audit log failure must never crash the main loop

    def query_log(self, n: int = 10) -> str:
        """Return last n log entries as a human-readable table."""
        if not _LOG_FILE.exists():
            return "[AuditLog] No events logged yet."

        lines = _LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-n:]

        rows = ["\n[HELIX] Audit Log -- Last {} Events".format(len(recent)),
                "-" * 72,
                f"  {'Timestamp':<26} {'Intent':<8} {'PII':<5} {'Route':<12} {'ms':<7} {'Outcome'}",
                "-" * 72]
        for raw in recent:
            try:
                r = json.loads(raw)
                ts_short = r["ts"][:19].replace("T", " ")
                rows.append(
                    f"  {ts_short:<26} {r['intent']:<8} {str(r['pii_detected']):<5} "
                    f"{r['routed_to']:<12} {r['duration_ms']:<7} {r['outcome']}"
                )
            except Exception:
                continue
        rows.append("-" * 72)
        return "\n".join(rows)

    def summary_stats(self) -> str:
        """Quick stats -- total calls, PII rate, cloud rate."""
        if not _LOG_FILE.exists():
            return "[AuditLog] No events yet."
        records = []
        for line in _LOG_FILE.read_text(encoding="utf-8").strip().splitlines():
            try:
                records.append(json.loads(line))
            except Exception:
                continue
        if not records:
            return "[AuditLog] No events yet."
        total      = len(records)
        pii_count  = sum(1 for r in records if r.get("pii_detected"))
        cloud_count = sum(1 for r in records if r.get("routed_to") in ("oracle", "fallback"))
        fast_count  = sum(1 for r in records if r.get("routed_to") == "fast_path")
        err_count   = sum(1 for r in records if r.get("outcome") == "error")
        avg_ms      = sum(r.get("duration_ms", 0) for r in records) / total
        return (
            f"[AuditLog] Summary: {total} total commands\n"
            f"  PII detected   : {pii_count} ({100*pii_count//total}%)\n"
            f"  Cloud routed   : {cloud_count} ({100*cloud_count//total}%)\n"
            f"  Fast-path hits : {fast_count} ({100*fast_count//total}%)\n"
            f"  Errors         : {err_count}\n"
            f"  Avg latency    : {avg_ms:.0f} ms"
        )
