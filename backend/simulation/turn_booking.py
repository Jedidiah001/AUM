"""Turn booking utilities for realistic alignment changes."""

from __future__ import annotations

from typing import Optional

from models.alignment import CrowdReaction, TurnType


def choose_turn_type(old_alignment: str, new_alignment: str, sudden: bool = False) -> TurnType:
    """Choose turn type from alignment transition."""
    if sudden:
        return TurnType.SUDDEN_BETRAYAL
    if old_alignment == "Face" and new_alignment == "Heel":
        return TurnType.CORRUPTION
    if old_alignment == "Heel" and new_alignment == "Face":
        return TurnType.REDEMPTION
    if "Tweener" in (old_alignment, new_alignment):
        return TurnType.TWEENER_TRANSITION
    return TurnType.GRADUAL_TURN


def infer_crowd_reaction(old_alignment: str, new_alignment: str, feud_intensity: Optional[int] = None) -> CrowdReaction:
    """Infer crowd reaction using simple wrestling psychology heuristics."""
    intensity = feud_intensity or 0
    if old_alignment == "Face" and new_alignment == "Heel":
        return CrowdReaction.HEAT if intensity >= 40 else CrowdReaction.MIXED
    if old_alignment == "Heel" and new_alignment == "Face":
        return CrowdReaction.POP if intensity >= 40 else CrowdReaction.MIXED
    return CrowdReaction.MIXED


def crowd_heat_score(feud_intensity: Optional[int] = None, base: int = 55) -> int:
    """Return 0-100 crowd heat score."""
    intensity = feud_intensity or 0
    return max(20, min(100, base + int(intensity * 0.35)))
