"""
Turn Routes - Alignment Turn Management
Handles API endpoints for wrestler face/heel turns, including initiation,
segment tracking, and resolution.
"""

from flask import Blueprint, jsonify, request, current_app
from models.alignment import (
    TurnType, TurnPhase, Alignment, CrowdReaction,
    determine_turn_type, calculate_popularity_impact
)
import traceback

turn_bp = Blueprint('turn', __name__)


def get_database():
    """Get database instance from app config"""
    return current_app.config['DATABASE']


def get_universe():
    """Get universe instance from app config"""
    return current_app.config['UNIVERSE']


def get_turn_manager():
    """Get turn manager from universe or app config"""
    universe = get_universe()
    if hasattr(universe, 'turn_manager'):
        return universe.turn_manager
    
    # Fallback to app config
    return current_app.config.get('TURN_MANAGER')


def get_turn_engine():
    """Get turn booking engine from app config"""
    return current_app.config.get('TURN_ENGINE')


@turn_bp.route('/api/turns')
def api_get_all_turns():
    """Get all turns (active and completed)"""
    try:
        turn_manager = get_turn_manager()
        
        if not turn_manager:
            return jsonify({
                'success': False,
                'error': 'Turn manager not initialized'
            }), 500
        
        return jsonify({
            'success': True,
            **turn_manager.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@turn_bp.route('/api/turns/active')
def api_get_active_turns():
    """Get all active (ongoing) turns"""
    try:
        turn_manager = get_turn_manager()
        active_turns = turn_manager.get_active_turns()
        
        return jsonify({
            'success': True,
            'total': len(active_turns),
            'turns': [t.to_dict() for t in active_turns]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@turn_bp.route('/api/turns/recent')
def api_get_recent_turns():
    """Get most recently completed turns"""
    try:
        turn_manager = get_turn_manager()
        limit = request.args.get('limit', 10, type=int)
        recent = turn_manager.get_recent_turns(limit)
        
        return jsonify({
            'success': True,
            'total': len(recent),
            'turns': [t.to_dict() for t in recent]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@turn_bp.route('/api/turns/<turn_id>')
def api_get_turn(turn_id):
    """Get a specific turn by ID"""
    try:
        turn_manager = get_turn_manager()
        turn = turn_manager.get_turn_by_id(turn_id)
        
        if not turn:
            return jsonify({
                'success': False,
                'error': 'Turn not found'
            }), 404
        
        return jsonify({
            'success': True,
            'turn': turn.to_dict()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@turn_bp.route('/api/turns/wrestler/<wrestler_id>')
def api_get_wrestler_turns(wrestler_id):
    """Get all turns involving a specific wrestler"""
    try:
        turn_manager = get_turn_manager()
        turns = turn_manager.get_turns_involving(wrestler_id)
        
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        wrestler_name = wrestler.name if wrestler else "Unknown"
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'total': len(turns),
            'turns': [t.to_dict() for t in turns]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@turn_bp.route('/api/turns/create', methods=['POST'])
def api_create_turn():
    """
    Create/initiate a new turn storyline.
    
    Expected JSON body:
    {
        "wrestler_id": "wrestler_001",
        "new_alignment": "Heel",  // Face, Heel, or Tweener
        "context": "betrayal",     // betrayal, redemption, corruption, transition
        "target_wrestler_ids": ["wrestler_002"],  // Optional
        "feud_id": "feud_123",     // Optional, related feud
        "storyline_id": "story_456",  // Optional, related storyline
        "is_sudden": true          // Whether this is immediate or gradual
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        wrestler_id = data.get('wrestler_id')
        new_alignment = data.get('new_alignment')
        context = data.get('context', 'corruption')
        target_ids = data.get('target_wrestler_ids', [])
        feud_id = data.get('feud_id')
        storyline_id = data.get('storyline_id')
        is_sudden = data.get('is_sudden', False)
        
        if not wrestler_id or not new_alignment:
            return jsonify({
                'success': False,
                'error': 'wrestler_id and new_alignment are required'
            }), 400
        
        universe = get_universe()
        turn_manager = get_turn_manager()
        feud_manager = universe.feud_manager if hasattr(universe, 'feud_manager') else None
        
        # Get wrestler
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if not wrestler:
            return jsonify({
                'success': False,
                'error': f'Wrestler {wrestler_id} not found'
            }), 404
        
        # Validate alignment
        if new_alignment not in ['Face', 'Heel', 'Tweener']:
            return jsonify({
                'success': False,
                'error': 'new_alignment must be Face, Heel, or Tweener'
            }), 400
        
        # Don't allow turn if already that alignment
        if wrestler.alignment == new_alignment:
            return jsonify({
                'success': False,
                'error': f'Wrestler is already {new_alignment}'
            }), 400
        
        # Get target wrestlers
        target_wrestlers = []
        target_names = []
        for tid in target_ids:
            tw = universe.get_wrestler_by_id(tid)
            if tw:
                target_wrestlers.append(tw)
                target_names.append(tw.name)
        
        # Get feud if specified
        feud = None
        if feud_id and feud_manager:
            feud = feud_manager.get_feud_by_id(feud_id)
        
        # Determine turn type
        if is_sudden or context == 'betrayal':
            turn_type = TurnType.SUDDEN_BETRAYAL
        elif context == 'redemption':
            turn_type = TurnType.REDEMPTION
        elif context == 'corruption':
            turn_type = TurnType.CORRUPTION
        else:
            turn_type = TurnType.GRADUAL_TURN
        
        # Create the turn
        from simulation.turn_booking import TurnBookingEngine
        
        engine = TurnBookingEngine(turn_manager, feud_manager)
        turn = engine.initiate_turn(
            wrestler=wrestler,
            new_alignment=new_alignment,
            context=context,
            target_wrestlers=target_wrestlers if target_wrestlers else None,
            feud=feud,
            storyline_id=storyline_id,
            year=universe.current_year,
            week=universe.current_week,
            show_id=None  # Will be set when segment is added
        )
        
        # Save to database
        database = get_database()
        if hasattr(database, 'save_turn_state'):
            database.save_turn_state(turn_manager.to_dict())
            database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Turn initiated for {wrestler.name}: {wrestler.alignment} → {new_alignment}',
            'turn': turn.to_dict(),
            'targets': target_names
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@turn_bp.route('/api/turns/<turn_id>/execute', methods=['POST'])
def api_execute_turn(turn_id):
    """
    Execute the actual turn moment (for gradual turns reaching climax).
    """
    try:
        data = request.get_json() or {}
        show_id = data.get('show_id')
        
        universe = get_universe()
        turn_manager = get_turn_manager()
        
        turn = turn_manager.get_turn_by_id(turn_id)
        if not turn:
            return jsonify({
                'success': False,
                'error': 'Turn not found'
            }), 404
        
        if turn.is_completed:
            return jsonify({
                'success': False,
                'error': 'Turn is already completed'
            }), 400
        
        # Execute the turn
        success = turn_manager.execute_turn_now(
            turn_id=turn_id,
            year=universe.current_year,
            week=universe.current_week,
            show_id=show_id
        )
        
        if success:
            # Save to database
            database = get_database()
            if hasattr(database, 'save_turn_state'):
                database.save_turn_state(turn_manager.to_dict())
                database.conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Turn executed! {turn.wrestler_name} has turned!',
                'turn': turn.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to execute turn'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@turn_bp.route('/api/turns/<turn_id>/resolve', methods=['POST'])
def api_resolve_turn(turn_id):
    """
    Resolve a turn and apply the new alignment permanently.
    """
    try:
        universe = get_universe()
        turn_manager = get_turn_manager()
        
        turn = turn_manager.get_turn_by_id(turn_id)
        if not turn:
            return jsonify({
                'success': False,
                'error': 'Turn not found'
            }), 404
        
        if not turn.is_completed and turn.turn_progress < 75:
            return jsonify({
                'success': False,
                'error': 'Turn is not ready to be resolved (needs more buildup)'
            }), 400
        
        # Get wrestler
        wrestler = universe.get_wrestler_by_id(turn.wrestler_id)
        if not wrestler:
            return jsonify({
                'success': False,
                'error': 'Wrestler not found'
            }), 404
        
        # Resolve the turn
        from simulation.turn_booking import TurnBookingEngine
        engine = TurnBookingEngine(turn_manager, universe.feud_manager)
        
        success, pop_change = engine.resolve_turn(
            turn_id=turn_id,
            wrestler=wrestler,
            year=universe.current_year,
            week=universe.current_week,
            apply_popularity_change=True
        )
        
        if success:
            # Save wrestler changes
            database = get_database()
            database.update_wrestler(wrestler)
            
            # Save turn state
            if hasattr(database, 'save_turn_state'):
                database.save_turn_state(turn_manager.to_dict())
                database.conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Turn resolved! {wrestler.name} is now {wrestler.alignment}',
                'turn': turn.to_dict(),
                'popularity_change': pop_change,
                'new_popularity': wrestler.popularity
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to resolve turn'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@turn_bp.route('/api/turns/<turn_id>/add_segment', methods=['POST'])
def api_add_turn_segment(turn_id):
    """
    Add a segment to an ongoing turn storyline.
    
    Expected JSON body:
    {
        "show_id": "show_123",
        "show_name": "ROC Alpha #52",
        "segment_type": "promo",  // promo, attack, match, confrontation
        "description": "Wrestler cuts a dark promo...",
        "crowd_reaction": "mixed",  // pop, heat, mixed, confused, silent, chant
        "crowd_heat_level": 75,  // 0-100
        "turn_progress": 20  // How much this advances the turn (0-100)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
        
        universe = get_universe()
        turn_manager = get_turn_manager()
        
        turn = turn_manager.get_turn_by_id(turn_id)
        if not turn:
            return jsonify({
                'success': False,
                'error': 'Turn not found'
            }), 404
        
        if turn.is_completed:
            return jsonify({
                'success': False,
                'error': 'Cannot add segments to completed turn'
            }), 400
        
        # Validate crowd reaction
        crowd_reaction_str = data.get('crowd_reaction', 'mixed')
        try:
            crowd_reaction = CrowdReaction(crowd_reaction_str)
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid crowd_reaction. Must be one of: {[r.value for r in CrowdReaction]}'
            }), 400
        
        # Add segment using engine
        from simulation.turn_booking import TurnBookingEngine
        engine = TurnBookingEngine(turn_manager, universe.feud_manager)
        
        segment = engine.add_turn_segment(
            turn_id=turn_id,
            show_id=data.get('show_id', ''),
            show_name=data.get('show_name', 'Unknown Show'),
            year=universe.current_year,
            week=universe.current_week,
            segment_type=data.get('segment_type', 'promo'),
            description=data.get('description', ''),
            crowd_reaction=crowd_reaction,
            crowd_heat_level=data.get('crowd_heat_level', 50),
            turn_progress=data.get('turn_progress', 10)
        )
        
        if segment:
            # Save to database
            database = get_database()
            if hasattr(database, 'save_turn_state'):
                database.save_turn_state(turn_manager.to_dict())
                database.conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Segment added to turn storyline',
                'segment': segment.to_dict(),
                'turn': turn.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add segment'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@turn_bp.route('/api/turns/report')
def api_get_turn_report():
    """Get comprehensive turn status report"""
    try:
        turn_manager = get_turn_manager()
        
        report = {
            'success': True,
            'total_turns': len(turn_manager.turns),
            'active_turns': len(turn_manager.get_active_turns()),
            'completed_turns': len([t for t in turn_manager.turns if t.is_completed]),
            'successful_turns': len(turn_manager.get_successful_turns()),
            'turns_by_type': {},
            'recent_turns': [],
            'active_turn_details': []
        }
        
        # Count by type
        for turn_type in TurnType:
            count = len(turn_manager.get_turns_by_type(turn_type))
            report['turns_by_type'][turn_type.value] = count
        
        # Recent completed turns
        recent = turn_manager.get_recent_turns(5)
        report['recent_turns'] = [t.to_dict() for t in recent]
        
        # Active turn details
        active = turn_manager.get_active_turns()
        report['active_turn_details'] = [t.to_dict() for t in active]
        
        return jsonify(report)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@turn_bp.route('/api/turns/simulate-reaction', methods=['POST'])
def api_simulate_crowd_reaction():
    """
    Simulate what crowd reaction would be for a potential turn.
    Useful for previewing before committing.
    
    Expected JSON body:
    {
        "wrestler_id": "wrestler_001",
        "segment_type": "attack",
        "turn_context": "betrayal",
        "is_surprise": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('wrestler_id'):
            return jsonify({
                'success': False,
                'error': 'wrestler_id is required'
            }), 400
        
        universe = get_universe()
        wrestler = universe.get_wrestler_by_id(data['wrestler_id'])
        
        if not wrestler:
            return jsonify({
                'success': False,
                'error': 'Wrestler not found'
            }), 404
        
        from simulation.turn_booking import TurnBookingEngine
        from models.alignment import TurnManager
        from models.feud import FeudManager
        
        # Create temporary engine for simulation
        turn_manager = TurnManager()
        feud_manager = universe.feud_manager
        engine = TurnBookingEngine(turn_manager, feud_manager)
        
        reaction, heat = engine.simulate_crowd_reaction(
            wrestler=wrestler,
            segment_type=data.get('segment_type', 'promo'),
            turn_context=data.get('turn_context', 'betrayal'),
            is_surprise=data.get('is_surprise', False)
        )
        
        # Calculate predicted popularity impact
        old_align = Alignment(wrestler.alignment)
        new_align_str = 'Heel' if wrestler.alignment == 'Face' else 'Face'
        new_align = Alignment(new_align_str)
        
        pop_impact = calculate_popularity_impact(
            old_alignment=old_align,
            new_alignment=new_align,
            crowd_reaction=reaction,
            wrestler_popularity=wrestler.popularity,
            is_successful=True
        )
        
        return jsonify({
            'success': True,
            'wrestler_id': wrestler.id,
            'wrestler_name': wrestler.name,
            'current_alignment': wrestler.alignment,
            'predicted_reaction': reaction.value,
            'predicted_heat_level': heat,
            'predicted_popularity_change': pop_impact,
            'interpretation': _get_reaction_interpretation(reaction, heat)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def _get_reaction_interpretation(reaction: CrowdReaction, heat: int) -> str:
    """Get human-readable interpretation of crowd reaction"""
    interpretations = {
        CrowdReaction.POP: f"Strong positive reaction! Crowd loves this ({heat}% intensity)",
        CrowdReaction.HEAT: f"Strong negative reaction! Crowd hates this ({heat}% intensity)",
        CrowdReaction.MIXED: f"Mixed reaction - crowd is divided ({heat}% intensity)",
        CrowdReaction.CONFUSED: f"Confused reaction - crowd doesn't understand ({heat}% intensity)",
        CrowdReaction.SILENT: f"Silent shock - crowd is stunned ({heat}% intensity)",
        CrowdReaction.CHANT: f"Crowd is chanting! Strong engagement ({heat}% intensity)"
    }
    return interpretations.get(reaction, "Unknown reaction")


@turn_bp.route('/api/turns/cancel/<turn_id>', methods=['POST'])
def api_cancel_turn(turn_id):
    """Cancel an ongoing turn storyline"""
    try:
        turn_manager = get_turn_manager()
        
        turn = turn_manager.get_turn_by_id(turn_id)
        if not turn:
            return jsonify({
                'success': False,
                'error': 'Turn not found'
            }), 404
        
        if turn.is_completed:
            return jsonify({
                'success': False,
                'error': 'Cannot cancel a completed turn'
            }), 400
        
        turn_manager.cancel_turn(turn_id)
        
        # Save to database
        database = get_database()
        if hasattr(database, 'save_turn_state'):
            database.save_turn_state(turn_manager.to_dict())
            database.conn.commit()
        
        return jsonify({
            'success': True,
            'message': f'Turn cancelled for {turn.wrestler_name}'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
