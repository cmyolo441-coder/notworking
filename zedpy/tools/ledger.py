"""ledger_update tool — model iske through Dream milestones ko track karta hai.

Model apni structural progress declare karta hai (milestone done/add), lekin asli
completion gate (fake_scan == 0, tests pass, double-verify) hard backstop rehta hai,
isliye model jhoot bolkar "done" tak nahi pahunch sakta.
"""
from __future__ import annotations

from .base import Tool


class LedgerUpdate(Tool):
    name = "ledger_update"
    requires_approval = False
    description = (
        "Update the Dream task ledger (the bounded, resumable engine's milestone list).\n"
        "  action='list' — show pending milestones.\n"
        "  action='done' — mark a milestone complete (item_id required). Mark done "
        "ONLY when that milestone's REAL working code exists and its tests pass.\n"
        "  action='add'  — add a new milestone (description required).\n"
        "The run continues within its hard cap until every milestone is done AND verification "
        "passes twice — so keep this ledger accurate as you finish real work."
    )

    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "done", "add"],
                    "description": "list | done | add",
                },
                "item_id": {
                    "type": "string",
                    "description": "Milestone id (e.g. 'm3') for action='done'.",
                },
                "description": {
                    "type": "string",
                    "description": "New milestone text for action='add'.",
                },
                "target": {
                    "type": "string",
                    "description": "Optional target/file hint for action='add'.",
                },
                "evidence": {
                    "type": "string",
                    "description": "Optional proof (test output, file path) for done.",
                },
            },
            "required": ["action"],
        }

    def run(self, workdir: str, action: str = "list", item_id: str = "",
            description: str = "", target: str = "", evidence: str = "",
            **_) -> str:
        from ..core import ledger

        if action == "list":
            data = ledger.load(workdir)
            return ledger.pending_summary(data, limit=40)
        if action == "done":
            if not item_id:
                return "Error: item_id required for action='done'."
            return ledger.mark_done(workdir, item_id, evidence)
        if action == "add":
            if not description:
                return "Error: description required for action='add'."
            return ledger.add_milestone(workdir, description, target)
        return f"Error: unknown action {action!r} (use list|done|add)."
