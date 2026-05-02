"""
Alignment & Turn System
Manages wrestler face/heel alignments with systematic turn tracking, buildup phases,
crowd reaction monitoring, and persistence.

This system integrates with feuds and storylines to create realistic wrestling
storytelling moments like WWE or AEW alignment changes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class Alignment(Enum):
    """Wrestler alignment types"""
    FACE = "Face"           # Good guy, fan favorite
    HEEL = "Heel"           # Bad guy, villain
    TWEENER = "Tweener"     # Morally ambiguous, between face and heel


class TurnType(Enum):
    """Types of alignment turns"""
    SUDDEN_BETRAYAL = "sudden_betrayal"      # Shocking turn (attack partner)
    GRADUAL_TURN = "gradual_turn"            # Slow build over weeks
    FORCED_TURN = "forced_turn"              # Circumstances force change
    REDEMPTION = "redemption"                # Heel turns face
    CORRUPTION = "corruption"                # Face turns heel
    TWEENER_TRANSITION = "tweener_transition" # Moving to neutral


class TurnPhase(Enum):
    """Phases of a turn storyline"""
    SETUP = "setup"              # Initial hints and teases
    BUILDUP = "buildup"          # Growing tension, mixed reactions
    EXECUTION = "execution"      # The actual turn happens
    AFTERMATH = "aftermath"      # Crowd reaction solidifies
    RESOLVED = "resolved"        # New alignment established


class CrowdReaction(Enum):
    """Crowd reaction types"""
    POP = "pop"                  # Loud cheers
    HEAT = "heat"                # Loud boos
    MIXED = "mixed"              # Split reaction
    CONFUSED = "confused"        # Uncertain reaction
    SILENT = "silent"            # Shocked silence
    CHANT = "chant"              # Organized chanting


@dataclass
class TurnSegment:
    """A segment in the turn storyline (promo, match, attack, etc.)"""
    segment_id: str
    show_id: str
    show_name: str
    year: int
    week: int
    segment_type: str  # 'promo', 'match', 'attack', 'interview', 'backstage'
    description: str
    crowd_reaction: CrowdReaction
    crowd_heat_level: int  # 0-100, intensity of reaction
    turn_progress: int  # How much this advanced the turn (0-100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'show_id': self.show_id,
            'show_name': self.show_name,
            'year': self.year,
            'week': self.week,
            'segment_type': self.segment_type,
            'description': self.description,
            'crowd_reaction': self.crowd_reaction.value,
            'crowd_heat_level': self.crowd_heat_level,
            'turn_progress': self.turn_progress
        }


@dataclass
class CrowdReactionHistory:
    """Tracks how crowd reactions evolved during a turn"""
    initial_reaction: CrowdReaction
    peak_heat: int  # Highest crowd reaction level (0-100)
    average_reaction: str  # Overall sentiment
    reaction_counts: Dict[str, int]  # Count of each reaction type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'initial_reaction': self.initial_reaction.value,
            'peak_heat': self.peak_heat,
            'average_reaction': self.average_reaction,
            'reaction_counts': self.reaction_counts
        }


class WrestlerTurn:
    """
    Represents an ongoing or completed alignment turn for a wrestler.
    
    Turns can be sudden (betrayal) or gradual (slow build), and track
    crowd reactions throughout the process.
    """
    
    def __init__(
        self,
        turn_id: str,
        wrestler_id: str,
        wrestler_name: str,
        turn_type: TurnType,
        old_alignment: Alignment,
        new_alignment: Alignment,
        year: int,
        week: int,
        show_id: Optional[str] = None,
        feud_id: Optional[str] = None,
        storyline_id: Optional[str] = None,
        target_wrestler_ids: Optional[List[str]] = None,
        target_wrestler_names: Optional[List[str]] = None
    ):
        self.id = turn_id
        self.wrestler_id = wrestler_id
        self.wrestler_name = wrestler_name
        self.turn_type = turn_type
        self.old_alignment = old_alignment
        self.new_alignment = new_alignment
        self.start_year = year
        self.start_week = week
        self.start_show_id = show_id
        
        # Related feud/storyline
        self.feud_id = feud_id
        self.storyline_id = storyline_id
        
        # Target of betrayal (if applicable)
        self.target_wrestler_ids = target_wrestler_ids or []
        self.target_wrestler_names = target_wrestler_names or []
        
        # Turn progression
        self.phase = TurnPhase.SETUP
        self.turn_progress = 0  # 0-100
        self.segments: List[TurnSegment] = []
        
        # Crowd reaction tracking
        self.crowd_history: Optional[CrowdReactionHistory] = None
        self.final_crowd_reaction: Optional[CrowdReaction] = None
        self.popularity_change: int = 0  # Net popularity gain/loss from turn
        
        # Timing
        self.execution_year: Optional[int] = None
        self.execution_week: Optional[int] = None
        self.execution_show_id: Optional[str] = None
        self.resolved_year: Optional[int] = None
        self.resolved_week: Optional[int] = None
        
        # Status
        self.is_completed = False
        self.is_successful = True  # Did the turn get over with fans?
    
    def add_segment(
        self,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        segment_type: str,
        description: str,
        crowd_reaction: CrowdReaction,
        crowd_heat_level: int,
        turn_progress: int = 0
    ) -> TurnSegment:
        """Add a segment to the turn storyline"""
        segment_id = f"{self.id}_seg_{len(self.segments) + 1:03d}"
        
        segment = TurnSegment(
            segment_id=segment_id,
            show_id=show_id,
            show_name=show_name,
            year=year,
            week=week,
            segment_type=segment_type,
            description=description,
            crowd_reaction=crowd_reaction,
            crowd_heat_level=crowd_heat_level,
            turn_progress=turn_progress
        )
        
        self.segments.append(segment)
        
        # Update phase based on progress
        if turn_progress > 0:
            self.turn_progress = max(self.turn_progress, turn_progress)
            self._update_phase()
        
        # Track crowd reaction
        self._track_crowd_reaction(crowd_reaction, crowd_heat_level)
        
        return segment
    
    def _update_phase(self):
        """Update turn phase based on progress"""
        if self.turn_progress >= 100:
            if self.phase != TurnPhase.RESOLVED:
                self.phase = TurnPhase.AFTERMATH
        elif self.turn_progress >= 75:
            self.phase = TurnPhase.EXECUTION
        elif self.turn_progress >= 40:
            self.phase = TurnPhase.BUILDUP
        elif self.turn_progress > 0:
            self.phase = TurnPhase.SETUP
    
    def _track_crowd_reaction(self, reaction: CrowdReaction, heat_level: int):
        """Track crowd reaction for history"""
        if self.crowd_history is None:
            self.crowd_history = CrowdReactionHistory(
                initial_reaction=reaction,
                peak_heat=heat_level,
                average_reaction=reaction.value,
                reaction_counts={
                    'pop': 0,
                    'heat': 0,
                    'mixed': 0,
                    'confused': 0,
                    'silent': 0,
                    'chant': 0
                }
            )
        
        # Update counts
        self.crowd_history.reaction_counts[reaction.value] += 1
        
        # Update peak heat
        if heat_level > self.crowd_history.peak_heat:
            self.crowd_history.peak_heat = heat_level
        
        # Calculate average reaction
        self._calculate_average_reaction()
    
    def _calculate_average_reaction(self):
        """Calculate the dominant crowd reaction"""
        if not self.crowd_history or not self.crowd_history.reaction_counts:
            return
        
        counts = self.crowd_history.reaction_counts
        total = sum(counts.values())
        
        if total == 0:
            return
        
        # Weight reactions
        weights = {
            'pop': 1.0,
            'heat': -1.0,
            'mixed': 0.0,
            'confused': -0.2,
            'silent': -0.5,
            'chant': 0.5
        }
        
        weighted_sum = sum(counts[k] * weights.get(k, 0) for k in counts)
        average = weighted_sum / total
        
        if average > 0.3:
            self.crowd_history.average_reaction = 'pop'
        elif average < -0.3:
            self.crowd_history.average_reaction = 'heat'
        elif average > 0.1:
            self.crowd_history.average_reaction = 'mixed_positive'
        elif average < -0.1:
            self.crowd_history.average_reaction = 'mixed_negative'
        else:
            self.crowd_history.average_reaction = 'mixed'
    
    def execute_turn(self, year: int, week: int, show_id: str):
        """Mark the turn as executed (the actual betrayal/change happens)"""
        self.execution_year = year
        self.execution_week = week
        self.execution_show_id = show_id
        self.phase = TurnPhase.EXECUTION
        self.turn_progress = 75
    
    def resolve_turn(self, year: int, week: int, popularity_change: int = 0):
        """Mark the turn as fully resolved and established"""
        self.resolved_year = year
        self.resolved_week = week
        self.phase = TurnPhase.RESOLVED
        self.turn_progress = 100
        self.is_completed = True
        self.popularity_change = popularity_change
        
        # Determine if turn was successful based on crowd reaction
        if self.crowd_history:
            avg = self.crowd_history.average_reaction
            # Successful if crowd reacted strongly (either pop or heat)
            self.is_successful = avg in ['pop', 'heat', 'mixed_positive', 'mixed_negative']
    
    def get_turn_duration_weeks(self) -> int:
        """Get how many weeks the turn took"""
        if not self.resolved_year:
            current_year = 1  # Would get from universe
            current_week = 1
            return (current_year - self.start_year) * 52 + (current_week - self.start_week)
        
        return (self.resolved_year - self.start_year) * 52 + (self.resolved_week - self.start_week)
    
    @property
    def is_gradual(self) -> bool:
        """Check if this is a gradual turn vs sudden"""
        return self.turn_type in [TurnType.GRADUAL_TURN, TurnType.FORCED_TURN]
    
    @property
    def is_sudden(self) -> bool:
        """Check if this is a sudden betrayal"""
        return self.turn_type == TurnType.SUDDEN_BETRAYAL
    
    @property
    def intensity_level(self) -> str:
        """Human-readable turn intensity"""
        if self.turn_progress >= 90:
            return "Complete"
        elif self.turn_progress >= 75:
            return "Executed"
        elif self.turn_progress >= 50:
            return "Heating Up"
        elif self.turn_progress >= 25:
            return "Building"
        else:
            return "Teasing"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize turn to dictionary"""
        return {
            'id': self.id,
            'wrestler_id': self.wrestler_id,
            'wrestler_name': self.wrestler_name,
            'turn_type': self.turn_type.value,
            'old_alignment': self.old_alignment.value,
            'new_alignment': self.new_alignment.value,
            'start_year': self.start_year,
            'start_week': self.start_week,
            'start_show_id': self.start_show_id,
            'feud_id': self.feud_id,
            'storyline_id': self.storyline_id,
            'target_wrestler_ids': self.target_wrestler_ids,
            'target_wrestler_names': self.target_wrestler_names,
            'phase': self.phase.value,
            'turn_progress': self.turn_progress,
            'intensity_level': self.intensity_level,
            'segments': [seg.to_dict() for seg in self.segments],
            'crowd_history': self.crowd_history.to_dict() if self.crowd_history else None,
            'final_crowd_reaction': self.final_crowd_reaction.value if self.final_crowd_reaction else None,
            'popularity_change': self.popularity_change,
            'execution_year': self.execution_year,
            'execution_week': self.execution_week,
            'execution_show_id': self.execution_show_id,
            'resolved_year': self.resolved_year,
            'resolved_week': self.resolved_week,
            'duration_weeks': self.get_turn_duration_weeks(),
            'is_completed': self.is_completed,
            'is_successful': self.is_successful,
            'is_gradual': self.is_gradual,
            'is_sudden': self.is_sudden
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WrestlerTurn':
        """Create turn from dictionary"""
        turn = WrestlerTurn(
            turn_id=data['id'],
            wrestler_id=data['wrestler_id'],
            wrestler_name=data['wrestler_name'],
            turn_type=TurnType(data['turn_type']),
            old_alignment=Alignment(data['old_alignment']),
            new_alignment=Alignment(data['new_alignment']),
            year=data['start_year'],
            week=data['start_week'],
            show_id=data.get('start_show_id'),
            feud_id=data.get('feud_id'),
            storyline_id=data.get('storyline_id'),
            target_wrestler_ids=data.get('target_wrestler_ids'),
            target_wrestler_names=data.get('target_wrestler_names')
        )
        
        turn.phase = TurnPhase(data.get('phase', 'setup'))
        turn.turn_progress = data.get('turn_progress', 0)
        turn.execution_year = data.get('execution_year')
        turn.execution_week = data.get('execution_week')
        turn.execution_show_id = data.get('execution_show_id')
        turn.resolved_year = data.get('resolved_year')
        turn.resolved_week = data.get('resolved_week')
        turn.popularity_change = data.get('popularity_change', 0)
        turn.is_completed = data.get('is_completed', False)
        turn.is_successful = data.get('is_successful', True)
        
        # Load segments
        for seg_data in data.get('segments', []):
            turn.segments.append(TurnSegment(
                segment_id=seg_data['segment_id'],
                show_id=seg_data['show_id'],
                show_name=seg_data['show_name'],
                year=seg_data['year'],
                week=seg_data['week'],
                segment_type=seg_data['segment_type'],
                description=seg_data['description'],
                crowd_reaction=CrowdReaction(seg_data['crowd_reaction']),
                crowd_heat_level=seg_data['crowd_heat_level'],
                turn_progress=seg_data.get('turn_progress', 0)
            ))
        
        # Load crowd history
        crowd_data = data.get('crowd_history')
        if crowd_data:
            turn.crowd_history = CrowdReactionHistory(
                initial_reaction=CrowdReaction(crowd_data['initial_reaction']),
                peak_heat=crowd_data['peak_heat'],
                average_reaction=crowd_data['average_reaction'],
                reaction_counts=crowd_data['reaction_counts']
            )
        
        final_reaction = data.get('final_crowd_reaction')
        if final_reaction:
            turn.final_crowd_reaction = CrowdReaction(final_reaction)
        
        return turn


class TurnManager:
    """Manages all wrestler turns in the universe"""
    
    def __init__(self):
        self.turns: List[WrestlerTurn] = []
        self._next_turn_id = 1
    
    def create_turn(
        self,
        wrestler_id: str,
        wrestler_name: str,
        turn_type: TurnType,
        old_alignment: Alignment,
        new_alignment: Alignment,
        year: int,
        week: int,
        show_id: Optional[str] = None,
        feud_id: Optional[str] = None,
        storyline_id: Optional[str] = None,
        target_wrestler_ids: Optional[List[str]] = None,
        target_wrestler_names: Optional[List[str]] = None,
        initial_progress: int = 0
    ) -> WrestlerTurn:
        """Create a new wrestler turn"""
        turn_id = f"turn_{self._next_turn_id:04d}"
        self._next_turn_id += 1
        
        turn = WrestlerTurn(
            turn_id=turn_id,
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            turn_type=turn_type,
            old_alignment=old_alignment,
            new_alignment=new_alignment,
            year=year,
            week=week,
            show_id=show_id,
            feud_id=feud_id,
            storyline_id=storyline_id,
            target_wrestler_ids=target_wrestler_ids,
            target_wrestler_names=target_wrestler_names
        )
        
        # For sudden betrayals, start at execution phase
        if turn_type == TurnType.SUDDEN_BETRAYAL:
            turn.turn_progress = 50
            turn.phase = TurnPhase.BUILDUP
        
        self.turns.append(turn)
        return turn
    
    def get_turn_by_id(self, turn_id: str) -> Optional[WrestlerTurn]:
        """Get turn by ID"""
        for turn in self.turns:
            if turn.id == turn_id:
                return turn
        return None
    
    def get_active_turns(self) -> List[WrestlerTurn]:
        """Get all turns that are not yet resolved"""
        return [t for t in self.turns if not t.is_completed]
    
    def get_turns_involving(self, wrestler_id: str) -> List[WrestlerTurn]:
        """Get all turns involving a specific wrestler (as turner or target)"""
        return [
            t for t in self.turns 
            if t.wrestler_id == wrestler_id or wrestler_id in t.target_wrestler_ids
        ]
    
    def get_recent_turns(self, limit: int = 10) -> List[WrestlerTurn]:
        """Get most recent completed turns"""
        completed = [t for t in self.turns if t.is_completed]
        completed.sort(key=lambda t: (t.resolved_year or 0, t.resolved_week or 0), reverse=True)
        return completed[:limit]
    
    def get_turns_by_type(self, turn_type: TurnType) -> List[WrestlerTurn]:
        """Get turns of a specific type"""
        return [t for t in self.turns if t.turn_type == turn_type]
    
    def get_successful_turns(self) -> List[WrestlerTurn]:
        """Get turns that were successful (got over with fans)"""
        return [t for t in self.turns if t.is_completed and t.is_successful]
    
    def cancel_turn(self, turn_id: str):
        """Cancel an ongoing turn storyline"""
        turn = self.get_turn_by_id(turn_id)
        if turn and not turn.is_completed:
            turn.is_completed = True
            turn.is_successful = False
            turn.phase = TurnPhase.RESOLVED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize all turns"""
        return {
            'total_turns': len(self.turns),
            'active_turns': len(self.get_active_turns()),
            'completed_turns': len([t for t in self.turns if t.is_completed]),
            'successful_turns': len(self.get_successful_turns()),
            'next_turn_id': self._next_turn_id,
            'turns': [t.to_dict() for t in self.turns]
        }
    
    def load_from_dict(self, data: Dict[str, Any]):
        """Load turns from dictionary"""
        self._next_turn_id = data.get('next_turn_id', 1)
        self.turns = []
        
        for turn_data in data.get('turns', []):
            turn = WrestlerTurn.from_dict(turn_data)
            self.turns.append(turn)


def determine_turn_type(
    context: str,
    has_feud: bool,
    has_storyline: bool,
    is_betrayal: bool
) -> TurnType:
    """
    Determine the appropriate turn type based on context.
    
    Args:
        context: 'betrayal', 'redemption', 'corruption', 'transition'
        has_feud: Whether there's an existing feud
        has_storyline: Whether there's a scripted storyline
        is_betrayal: Whether this involves betraying someone
    
    Returns:
        Appropriate TurnType enum value
    """
    if is_betrayal and context == 'betrayal':
        return TurnType.SUDDEN_BETRAYAL
    
    if context == 'redemption':
        return TurnType.REDEMPTION
    
    if context == 'corruption':
        return TurnType.CORRUPTION
    
    if has_storyline:
        return TurnType.GRADUAL_TURN
    
    if has_feud:
        return TurnType.FORCED_TURN
    
    return TurnType.TWEENER_TRANSITION


def calculate_popularity_impact(
    old_alignment: Alignment,
    new_alignment: Alignment,
    crowd_reaction: CrowdReaction,
    wrestler_popularity: int,
    is_successful: bool
) -> int:
    """
    Calculate popularity change from a turn.
    
    Returns:
        Popularity change (-50 to +50)
    """
    base_change = 0
    
    # Base impact based on direction
    if old_alignment == Alignment.HEEL and new_alignment == Alignment.FACE:
        # Redemption usually popular
        base_change = 15
    elif old_alignment == Alignment.FACE and new_alignment == Alignment.HEEL:
        # Turning heel can lose fans but gain heat
        base_change = -10
    elif new_alignment == Alignment.TWEENER:
        # Tweener is often divisive
        base_change = 5
    
    # Crowd reaction modifier
    reaction_modifiers = {
        CrowdReaction.POP: 20,
        CrowdReaction.HEAT: -15,
        CrowdReaction.MIXED: 0,
        CrowdReaction.CONFUSED: -10,
        CrowdReaction.SILENT: -20,
        CrowdReaction.CHANT: 10
    }
    base_change += reaction_modifiers.get(crowd_reaction, 0)
    
    # Success modifier
    if is_successful:
        base_change = int(base_change * 1.2)
    else:
        base_change = int(base_change * 0.5)
    
    # Clamp to reasonable range
    return max(-50, min(50, base_change))
