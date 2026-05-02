from __future__ import annotations

import random
from typing import Dict, Any

from models.alignment import CrowdReaction, TurnPhase, calculate_popularity_impact


class TurnBookingEngine:
    """Simulates realistic turn beats and crowd reaction outcomes."""

    def __init__(self, universe):
        self.universe = universe

    def advance_turn(self, turn, show_id: str, show_name: str, segment_type: str, crowd_reaction: CrowdReaction) -> Dict[str, Any]:
        progress_gain = self._progress_gain(turn.phase, segment_type, crowd_reaction)
        new_progress = min(100, turn.turn_progress + progress_gain)
        description = self._description(turn, segment_type, crowd_reaction)

        turn.add_segment(
            show_id=show_id,
            show_name=show_name,
            year=self.universe.current_year,
            week=self.universe.current_week,
            segment_type=segment_type,
            description=description,
            crowd_reaction=crowd_reaction,
            crowd_heat_level=self._heat_from_reaction(crowd_reaction),
            turn_progress=new_progress,
        )

        if turn.phase == TurnPhase.EXECUTION and turn.execution_week is None:
            turn.execute_turn(self.universe.current_year, self.universe.current_week, show_id)

        if new_progress >= 100 and not turn.is_completed:
            turn.final_crowd_reaction = crowd_reaction
            wrestler = self.universe.get_wrestler_by_id(turn.wrestler_id)
            popularity_change = calculate_popularity_impact(
                old_alignment=turn.old_alignment,
                new_alignment=turn.new_alignment,
                crowd_reaction=crowd_reaction,
                wrestler_popularity=wrestler.stats.popularity if wrestler else 50,
                is_successful=True,
            )
            turn.resolve_turn(self.universe.current_year, self.universe.current_week, popularity_change)
            if wrestler:
                wrestler.alignment = turn.new_alignment.value
                wrestler.adjust_popularity(popularity_change)
                self.universe.save_wrestler(wrestler)
            self._trigger_feud_post_turn(turn)

        return {'turn': turn.to_dict(), 'progress_gain': progress_gain, 'description': description}

    def execute_immediate_turn(
        self,
        turn,
        show_id: str,
        show_name: str,
        crowd_reaction: CrowdReaction = CrowdReaction.HEAT
    ) -> Dict[str, Any]:
        """Immediately execute and resolve a turn in one action."""
        turn.execute_turn(self.universe.current_year, self.universe.current_week, show_id)
        return self.advance_turn(
            turn=turn,
            show_id=show_id,
            show_name=show_name,
            segment_type='attack',
            crowd_reaction=crowd_reaction
        )

    def _trigger_feud_post_turn(self, turn):
        if turn.feud_id:
            feud = self.universe.feud_manager.get_feud_by_id(turn.feud_id)
            if feud:
                feud.adjust_intensity(20)
                feud.add_segment(
                    show_id=f"show_y{self.universe.current_year}_w{self.universe.current_week}",
                    show_name=f"Week {self.universe.current_week} Show",
                    year=self.universe.current_year,
                    week=self.universe.current_week,
                    segment_type='betrayal_aftermath',
                    description=f"{turn.wrestler_name}'s turn escalates the feud.",
                    intensity_change=15,
                )
                self.universe.save_feud(feud)

    @staticmethod
    def _progress_gain(phase, segment_type: str, reaction: CrowdReaction) -> int:
        base = {'promo': 12, 'match': 18, 'attack': 28, 'interview': 10, 'backstage': 14}.get(segment_type, 10)
        reaction_mod = {CrowdReaction.POP: 8, CrowdReaction.HEAT: 10, CrowdReaction.MIXED: 4, CrowdReaction.CONFUSED: -3, CrowdReaction.SILENT: -5, CrowdReaction.CHANT: 12}[reaction]
        phase_mod = {TurnPhase.SETUP: 1.2, TurnPhase.BUILDUP: 1.0, TurnPhase.EXECUTION: 0.8, TurnPhase.AFTERMATH: 0.6, TurnPhase.RESOLVED: 0.0}[phase]
        return max(1, int((base + reaction_mod + random.randint(-3, 3)) * phase_mod))

    @staticmethod
    def _heat_from_reaction(reaction: CrowdReaction) -> int:
        return {CrowdReaction.POP: 85, CrowdReaction.HEAT: 90, CrowdReaction.MIXED: 65, CrowdReaction.CONFUSED: 45, CrowdReaction.SILENT: 35, CrowdReaction.CHANT: 95}[reaction]

    @staticmethod
    def _description(turn, segment_type: str, crowd_reaction: CrowdReaction) -> str:
        return f"{turn.wrestler_name} delivers a {segment_type} beat in the turn arc; crowd reaction: {crowd_reaction.value}."
