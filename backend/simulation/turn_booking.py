"""
Turn Booking Simulation
Handles the simulation and booking of alignment turns, including crowd reaction
generation, feud integration, and storyline triggers.
"""

import random
from typing import List, Dict, Any, Optional, Tuple
from models.alignment import (
    WrestlerTurn, TurnManager, TurnType, TurnPhase, Alignment,
    CrowdReaction, determine_turn_type, calculate_popularity_impact, TurnSegment
)
from models.wrestler import Wrestler
from models.feud import Feud, FeudType, FeudManager


class TurnBookingEngine:
    """
    Engine for booking and simulating wrestler turns.
    Integrates with feuds, storylines, and roster management.
    """
    
    def __init__(self, turn_manager: TurnManager, feud_manager: FeudManager):
        self.turn_manager = turn_manager
        self.feud_manager = feud_manager
    
    def initiate_turn(
        self,
        wrestler: Wrestler,
        new_alignment: str,
        context: str = "corruption",
        target_wrestlers: Optional[List[Wrestler]] = None,
        feud: Optional[Feud] = None,
        storyline_id: Optional[str] = None,
        year: int = 1,
        week: int = 1,
        show_id: Optional[str] = None
    ) -> WrestlerTurn:
        """
        Initiate a new turn storyline for a wrestler.
        
        Args:
            wrestler: The wrestler turning
            new_alignment: New alignment ('Face', 'Heel', 'Tweener')
            context: Context of turn ('betrayal', 'redemption', 'corruption', 'transition')
            target_wrestlers: Wrestlers being betrayed/targeted
            feud: Related feud if any
            storyline_id: Related storyline ID if any
            year: Current year
            week: Current week
            show_id: Current show ID
        
        Returns:
            Created WrestlerTurn object
        """
        old_alignment = Alignment(wrestler.alignment)
        new_align = Alignment(new_alignment)
        
        # Determine turn type
        is_betrayal = context == "betrayal" and target_wrestlers is not None
        has_feud = feud is not None
        has_storyline = storyline_id is not None
        
        turn_type = determine_turn_type(
            context=context,
            has_feud=has_feud,
            has_storyline=has_storyline,
            is_betrayal=is_betrayal
        )
        
        # Prepare target data
        target_ids = [t.id for t in target_wrestlers] if target_wrestlers else []
        target_names = [t.name for t in target_wrestlers] if target_wrestlers else []
        
        # Create the turn
        turn = self.turn_manager.create_turn(
            wrestler_id=wrestler.id,
            wrestler_name=wrestler.name,
            turn_type=turn_type,
            old_alignment=old_alignment,
            new_alignment=new_align,
            year=year,
            week=week,
            show_id=show_id,
            feud_id=feud.id if feud else None,
            storyline_id=storyline_id,
            target_wrestler_ids=target_ids,
            target_wrestler_names=target_names
        )
        
        # If sudden betrayal, execute immediately
        if turn_type == TurnType.SUDDEN_BETRAYAL:
            turn.execute_turn(year, week, show_id)
            
            # Auto-create or intensify feud with targets
            if target_wrestlers:
                self._create_betrayal_feud(wrestler, target_wrestlers, year, week, show_id)
        
        return turn
    
    def _create_betrayal_feud(
        self,
        betrayer: Wrestler,
        victims: List[Wrestler],
        year: int,
        week: int,
        show_id: str
    ):
        """Create or intensify feud from a betrayal"""
        for victim in victims:
            # Check if feud already exists
            existing = self.feud_manager.get_feud_between(betrayer.id, victim.id)
            
            if existing:
                # Intensify existing feud
                existing.add_segment(
                    show_id=show_id,
                    show_name="Recent Show",
                    year=year,
                    week=week,
                    segment_type='attack',
                    description=f"BETRAYAL! {betrayer.name} attacked their former partner {victim.name}!",
                    intensity_change=30
                )
            else:
                # Create new feud
                self.feud_manager.create_feud(
                    feud_type=FeudType.TAG_TEAM_BREAKUP,
                    participant_ids=[betrayer.id, victim.id],
                    participant_names=[betrayer.name, victim.name],
                    year=year,
                    week=week,
                    show_id=show_id,
                    initial_intensity=60
                )
    
    def add_turn_segment(
        self,
        turn_id: str,
        show_id: str,
        show_name: str,
        year: int,
        week: int,
        segment_type: str,
        description: str,
        crowd_reaction: CrowdReaction,
        crowd_heat_level: int,
        turn_progress: int
    ) -> Optional[TurnSegment]:
        """
        Add a segment to an ongoing turn storyline.
        
        Args:
            turn_id: ID of the turn
            show_id: Show where segment occurred
            show_name: Name of the show
            year: Current year
            week: Current week
            segment_type: Type of segment ('promo', 'match', 'attack', etc.)
            description: Description of what happened
            crowd_reaction: How the crowd reacted
            crowd_heat_level: Intensity of crowd reaction (0-100)
            turn_progress: How much this advanced the turn (0-100)
        
        Returns:
            Created TurnSegment or None if turn not found
        """
        from models.alignment import TurnSegment
        
        turn = self.turn_manager.get_turn_by_id(turn_id)
        if not turn or turn.is_completed:
            return None
        
        segment = turn.add_segment(
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
        
        return segment
    
    def execute_turn_now(
        self,
        turn_id: str,
        year: int,
        week: int,
        show_id: str
    ) -> bool:
        """
        Execute the actual turn (the moment of betrayal/change).
        
        Args:
            turn_id: ID of the turn
            year: Current year
            week: Current week
            show_id: Current show ID
        
        Returns:
            True if successful, False if turn not found or already completed
        """
        turn = self.turn_manager.get_turn_by_id(turn_id)
        if not turn or turn.is_completed:
            return False
        
        turn.execute_turn(year, week, show_id)
        return True
    
    def resolve_turn(
        self,
        turn_id: str,
        wrestler: Wrestler,
        year: int,
        week: int,
        apply_popularity_change: bool = True
    ) -> Tuple[bool, int]:
        """
        Resolve a turn and apply the new alignment.
        
        Args:
            turn_id: ID of the turn
            wrestler: The wrestler who turned
            year: Current year
            week: Current week
            apply_popularity_change: Whether to apply popularity change
        
        Returns:
            Tuple of (success, popularity_change)
        """
        turn = self.turn_manager.get_turn_by_id(turn_id)
        if not turn or not turn.is_completed:
            return False, 0
        
        # Determine final crowd reaction
        if turn.crowd_history:
            avg = turn.crowd_history.average_reaction
            reaction_map = {
                'pop': CrowdReaction.POP,
                'heat': CrowdReaction.HEAT,
                'mixed': CrowdReaction.MIXED,
                'mixed_positive': CrowdReaction.MIXED,
                'mixed_negative': CrowdReaction.MIXED,
                'confused': CrowdReaction.CONFUSED,
                'silent': CrowdReaction.SILENT
            }
            turn.final_crowd_reaction = reaction_map.get(avg, CrowdReaction.MIXED)
        
        # Calculate popularity impact
        pop_change = 0
        if apply_popularity_change and turn.final_crowd_reaction:
            pop_change = calculate_popularity_impact(
                old_alignment=turn.old_alignment,
                new_alignment=turn.new_alignment,
                crowd_reaction=turn.final_crowd_reaction,
                wrestler_popularity=wrestler.popularity,
                is_successful=turn.is_successful
            )
        
        # Resolve the turn
        turn.resolve_turn(year, week, pop_change)
        
        # Apply new alignment to wrestler
        wrestler.alignment = turn.new_alignment.value
        
        # Apply popularity change
        if apply_popularity_change:
            wrestler.adjust_popularity(pop_change)
        
        return True, pop_change
    
    def simulate_crowd_reaction(
        self,
        wrestler: Wrestler,
        segment_type: str,
        turn_context: str,
        is_surprise: bool = False
    ) -> Tuple[CrowdReaction, int]:
        """
        Simulate crowd reaction to a turn segment.
        
        Args:
            wrestler: The wrestler involved
            segment_type: Type of segment ('promo', 'attack', 'match')
            turn_context: Context ('betrayal', 'redemption', etc.)
            is_surprise: Whether this is a shocking moment
        
        Returns:
            Tuple of (CrowdReaction, heat_level 0-100)
        """
        base_factors = {
            'Face': {'pop_base': 0.4, 'heat_base': 0.2},
            'Heel': {'pop_base': 0.2, 'heat_base': 0.4},
            'Tweener': {'pop_base': 0.3, 'heat_base': 0.3}
        }
        
        factors = base_factors.get(wrestler.alignment, base_factors['Tweener'])
        
        # Adjust for context
        if turn_context == 'betrayal':
            if wrestler.alignment == 'Face':
                # Face betraying = shock, mixed reaction
                factors['heat_base'] += 0.2
                factors['pop_base'] -= 0.1
            else:
                # Heel betraying = expected heat
                factors['heat_base'] += 0.1
        elif turn_context == 'redemption':
            # Heel turning face = potential pop
            factors['pop_base'] += 0.2
            factors['heat_base'] -= 0.1
        
        # Surprise factor
        if is_surprise:
            # Surprise moments get stronger reactions
            surprise_roll = random.random()
            if surprise_roll > 0.5:
                factors['pop_base'] += 0.15
                factors['heat_base'] += 0.15
        
        # Popularity modifier
        pop_mod = (wrestler.popularity - 50) / 200  # -0.25 to +0.25
        factors['pop_base'] += pop_mod
        
        # Determine reaction
        roll = random.random()
        cumulative = 0.0
        
        reaction_order = [
            (factors['pop_base'], CrowdReaction.POP),
            (factors['heat_base'], CrowdReaction.HEAT),
            (0.15, CrowdReaction.MIXED),
            (0.08, CrowdReaction.CHANT),
            (0.07, CrowdReaction.CONFUSED),
            (0.05, CrowdReaction.SILENT)
        ]
        
        for chance, reaction in reaction_order:
            cumulative += max(0, chance)
            if roll <= cumulative:
                # Calculate heat level based on wrestler popularity and randomness
                base_heat = 50 + (wrestler.popularity - 50) * 0.5
                heat_variation = random.randint(-15, 15)
                heat_level = max(10, min(100, int(base_heat + heat_variation)))
                
                # Surprise moments have higher heat
                if is_surprise:
                    heat_level = min(100, heat_level + 20)
                
                return reaction, heat_level
        
        # Default to mixed
        return CrowdReaction.MIXED, 50
    
    def generate_turn_segments_for_show(
        self,
        show_type: str,
        brand: str,
        universe_state,
        year: int,
        week: int
    ) -> List[Dict[str, Any]]:
        """
        Generate turn-related segments for a show.
        Called during show production.
        
        Args:
            show_type: Type of show ('weekly_tv', 'ppv', 'special')
            brand: Brand name
            universe_state: Universe state object
            year: Current year
            week: Current week
        
        Returns:
            List of segment dictionaries
        """
        segments = []
        active_turns = self.turn_manager.get_active_turns()
        
        for turn in active_turns:
            # Skip if turn doesn't involve wrestlers from this brand
            wrestler = universe_state.get_wrestler_by_id(turn.wrestler_id)
            if not wrestler or (brand != 'Cross-Brand' and wrestler.primary_brand != brand):
                continue
            
            # Determine if this turn needs a segment this week
            weeks_since_start = (year - turn.start_year) * 52 + (week - turn.start_week)
            
            # Segment frequency based on turn phase
            segment_needed = False
            segment_type = 'promo'
            description = ""
            progress_gain = 0
            
            if turn.phase == TurnPhase.SETUP:
                # Subtle hints every 2 weeks
                if weeks_since_start % 2 == 0 and weeks_since_start > 0:
                    segment_needed = True
                    segment_type = 'promo'
                    description = f"{wrestler.name} cuts a cryptic promo hinting at dissatisfaction..."
                    progress_gain = 15
            
            elif turn.phase == TurnPhase.BUILDUP:
                # More frequent segments, building tension
                if weeks_since_start % 1 == 0:
                    segment_needed = True
                    if turn.turn_type == TurnType.SUDDEN_BETRAYAL:
                        segment_type = 'attack'
                        description = f"{wrestler.name} shows aggression toward their partners!"
                    else:
                        segment_type = 'confrontation'
                        description = f"Tension rises as {wrestler.name} confronts their rivals..."
                    progress_gain = 20
            
            elif turn.phase == TurnPhase.EXECUTION:
                # The big moment - should happen soon
                if weeks_since_start <= 1:
                    segment_needed = True
                    segment_type = 'betrayal'
                    if turn.target_wrestler_names:
                        description = f"SHOCKING BETRAYAL! {wrestler.name} attacks {turn.target_wrestler_names[0]}!"
                    else:
                        description = f"{wrestler.name} makes a shocking alignment change!"
                    progress_gain = 50
            
            if segment_needed:
                # Simulate crowd reaction
                is_surprise = turn.phase == TurnPhase.EXECUTION
                reaction, heat = self.simulate_crowd_reaction(
                    wrestler=wrestler,
                    segment_type=segment_type,
                    turn_context=turn.turn_type.value,
                    is_surprise=is_surprise
                )
                
                segments.append({
                    'turn_id': turn.id,
                    'segment_type': segment_type,
                    'description': description,
                    'wrestler_id': wrestler.id,
                    'wrestler_name': wrestler.name,
                    'crowd_reaction': reaction.value,
                    'crowd_heat': heat,
                    'progress_gain': progress_gain,
                    'priority': 80 if turn.phase == TurnPhase.EXECUTION else 60
                })
        
        return segments
    
    def get_turn_status_report(self) -> Dict[str, Any]:
        """Get comprehensive report on all turns"""
        active = self.turn_manager.get_active_turns()
        recent = self.turn_manager.get_recent_turns(5)
        
        return {
            'total_turns': len(self.turn_manager.turns),
            'active_turns': len(active),
            'completed_turns': len(self.turn_manager.turns) - len(active),
            'successful_turns': len(self.turn_manager.get_successful_turns()),
            'active_turn_details': [t.to_dict() for t in active],
            'recent_completed': [t.to_dict() for t in recent],
            'turns_by_type': {
                'sudden_betrayals': len(self.turn_manager.get_turns_by_type(TurnType.SUDDEN_BETRAYAL)),
                'gradual_turns': len(self.turn_manager.get_turns_by_type(TurnType.GRADUAL_TURN)),
                'redemptions': len(self.turn_manager.get_turns_by_type(TurnType.REDEMPTION)),
                'corruptions': len(self.turn_manager.get_turns_by_type(TurnType.CORRUPTION))
            }
        }


def create_turn_from_feud(
    feud: Feud,
    winner: Wrestler,
    loser: Wrestler,
    year: int,
    week: int,
    show_id: str,
    turn_manager: TurnManager,
    feud_manager: FeudManager,
    forced_turn: bool = False
) -> Optional[WrestlerTurn]:
    """
    Create a turn storyline from an intense feud.
    
    Args:
        feud: The feud that's prompting the turn
        winner: Winner of a key match
        loser: Loser of the match
        year: Current year
        week: Current week
        show_id: Current show ID
        turn_manager: TurnManager instance
        feud_manager: FeudManager instance
        forced_turn: Whether circumstances force a turn
    
    Returns:
        Created WrestlerTurn or None
    """
    # Only create turn if feud is hot enough
    if feud.intensity < 70:
        return None
    
    # Decide who turns (usually the loser in frustration, or winner in arrogance)
    turner = loser if random.random() > 0.5 else winner
    victim = winner if turner == loser else loser
    
    # Determine new alignment
    if turner.alignment == 'Face':
        new_alignment = 'Heel'  # Frustration/corruption
        context = 'corruption'
    elif turner.alignment == 'Heel':
        new_alignment = 'Face'  # Redemption arc
        context = 'redemption'
    else:
        # Tweener goes either way
        new_alignment = random.choice(['Face', 'Heel'])
        context = 'transition'
    
    # Create the turn
    engine = TurnBookingEngine(turn_manager, feud_manager)
    turn = engine.initiate_turn(
        wrestler=turner,
        new_alignment=new_alignment,
        context=context,
        target_wrestlers=[victim],
        feud=feud,
        year=year,
        week=week,
        show_id=show_id
    )
    
    return turn
