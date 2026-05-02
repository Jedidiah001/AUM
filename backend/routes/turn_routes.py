from flask import Blueprint, jsonify, request, current_app

from models.alignment import Alignment, CrowdReaction, TurnType, determine_turn_type
from simulation.turn_booking import TurnBookingEngine

turn_bp = Blueprint('turn', __name__)


def get_universe():
    return current_app.config['UNIVERSE']


@turn_bp.route('/api/turns', methods=['GET'])
def api_get_turns():
    universe = get_universe()
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    turns = universe.turn_manager.get_active_turns() if active_only else universe.turn_manager.turns
    return jsonify({'total': len(turns), 'turns': [t.to_dict() for t in turns]})


@turn_bp.route('/api/turns/roster-context/<wrestler_id>', methods=['GET'])
def api_turn_context(wrestler_id):
    universe = get_universe()
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404

    active_feuds = [f for f in universe.feud_manager.get_feuds_involving(wrestler_id) if f.is_active]
    storyline_engine = current_app.config.get('STORYLINE_ENGINE')
    active_storylines = [s for s in storyline_engine.get_active_storylines() if wrestler_id in getattr(s, 'participants', [])] if storyline_engine else []

    return jsonify({
        'wrestler_id': wrestler.id,
        'wrestler_name': wrestler.name,
        'alignment': wrestler.alignment,
        'active_feuds': [f.to_dict() for f in active_feuds],
        'suggested_targets': [{'id': p, 'name': n} for feud in active_feuds for p, n in zip(feud.participant_ids, feud.participant_names) if p != wrestler_id],
        'active_storylines': [s.to_dict() for s in active_storylines],
    })


@turn_bp.route('/api/turns/create', methods=['POST'])
def api_create_turn():
    universe = get_universe()
    data = request.get_json(force=True)
    wrestler = universe.get_wrestler_by_id(data.get('wrestler_id'))
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404

    new_alignment = Alignment(data.get('new_alignment'))
    old_alignment = Alignment(wrestler.alignment)
    target_ids = data.get('target_wrestler_ids', [])
    targets = [universe.get_wrestler_by_id(tid) for tid in target_ids]
    target_names = [t.name for t in targets if t]

    has_feud = bool(data.get('feud_id'))
    has_storyline = bool(data.get('storyline_id'))
    is_betrayal = bool(target_ids)
    turn_type = TurnType(data['turn_type']) if data.get('turn_type') else determine_turn_type(
        data.get('context', 'transition'), has_feud, has_storyline, is_betrayal
    )

    turn = universe.turn_manager.create_turn(
        wrestler_id=wrestler.id,
        wrestler_name=wrestler.name,
        turn_type=turn_type,
        old_alignment=old_alignment,
        new_alignment=new_alignment,
        year=universe.current_year,
        week=universe.current_week,
        feud_id=data.get('feud_id'),
        storyline_id=data.get('storyline_id'),
        target_wrestler_ids=target_ids,
        target_wrestler_names=target_names,
    )

    universe.save_turn_state()
    return jsonify({'success': True, 'turn': turn.to_dict()})


@turn_bp.route('/api/turns/<turn_id>/simulate-segment', methods=['POST'])
def api_simulate_turn_segment(turn_id):
    universe = get_universe()
    turn = universe.turn_manager.get_turn_by_id(turn_id)
    if not turn:
        return jsonify({'error': 'Turn not found'}), 404

    payload = request.get_json(silent=True) or {}
    segment_type = payload.get('segment_type', 'promo')
    show_name = payload.get('show_name', f'Week {universe.current_week} Show')
    show_id = payload.get('show_id', f'show_y{universe.current_year}_w{universe.current_week}')
    crowd_reaction = CrowdReaction(payload.get('crowd_reaction', 'mixed'))

    engine = TurnBookingEngine(universe)
    result = engine.advance_turn(
        turn=turn,
        show_id=show_id,
        show_name=show_name,
        segment_type=segment_type,
        crowd_reaction=crowd_reaction,
    )
    universe.save_turn_state()
    return jsonify({'success': True, **result})
