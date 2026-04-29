"""Serialization helpers for ScoreResult explanation dicts."""

from __future__ import annotations

import json
from typing import Any


def explanation_to_json(explanation: dict[str, Any]) -> str:
    """Serialize score explanation dict to JSON string for database storage."""
    return json.dumps(explanation, indent=2)


def explanation_from_json(json_str: str) -> dict[str, Any]:
    """Deserialize score explanation from database JSON string."""
    return json.loads(json_str)


def explanation_to_text(explanation: dict[str, Any], total_score: float) -> str:
    """Human-readable multi-line text summary of score breakdown."""
    lines = [f"Total Score: {total_score:.1f}/100", ""]
    for dim, detail in explanation.items():
        pts = detail.get("points", 0)
        reason = detail.get("reason", "")
        lines.append(f"  {dim}: {pts:+d} pts — {reason}")
    return "\n".join(lines)
