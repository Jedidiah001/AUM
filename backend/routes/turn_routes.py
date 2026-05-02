"""Turn Routes - alignment turn lifecycle APIs."""

from flask import Blueprint, current_app, jsonify, request

from models.alignment import Alignment, CrowdReaction, TurnManager
from simulation.turn_booking import choose_turn_type, infer_crowd_reaction, crowd_heat_score

turn_bp = Blueprint("turn", __name__)


def _universe():
    return current_app.config["UNIVERSE"]


def _turn_manager() -> TurnManager:
    return _universe().turn_manager


@turn_bp.route('/api/turns', methods=['GET'])
def list_turns():
    return jsonify(_turn_manager().to_dict())


@turn_bp.route('/api/turns/initiate', methods=['POST'])
def initiate_turn():
    payload = request.get_json(silent=True) or {}
    wrestler_id = payload.get('wrestler_id')
    new_alignment = payload.get('new_alignment')
    if not wrestler_id or new_alignment not in {a.value for a in Alignment}:
        return jsonify({'error': 'wrestler_id and valid new_alignment are required'}), 400

    universe = _universe()
    wrestler = universe.get_wrestler_by_id(wrestler_id)
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404
    old_alignment = wrestler.alignment
    if old_alignment == new_alignment:
        return jsonify({'error': 'Wrestler is already on that alignment'}), 400

    feud = universe.feud_manager.get_primary_feud_for_wrestler(wrestler_id)
    feud_intensity = feud.intensity if feud else 0
    target_ids = feud.participant_ids if feud else []
    target_names = feud.participant_names if feud else []

    turn = _turn_manager().create_turn(
        wrestler_id=wrestler.id,
        wrestler_name=wrestler.name,
        turn_type=choose_turn_type(old_alignment, new_alignment, bool(payload.get('sudden', False))),
        old_alignment=Alignment(old_alignment),
        new_alignment=Alignment(new_alignment),
        year=universe.current_year,
        week=universe.current_week,
        feud_id=feud.id if feud else None,
        target_wrestler_ids=[i for i in target_ids if i != wrestler.id],
        target_wrestler_names=[n for i, n in zip(target_ids, target_names) if i != wrestler.id],
    )

    turn.add_segment(
        show_id=payload.get('show_id', 'office'),
        show_name=payload.get('show_name', 'Office Decision'),
        year=universe.current_year,
        week=universe.current_week,
        segment_type='setup',
        description=payload.get('description', f"Hints emerge that {wrestler.name} may change attitude."),
        crowd_reaction=infer_crowd_reaction(old_alignment, new_alignment, feud_intensity),
        crowd_heat_level=crowd_heat_score(feud_intensity, 45),
        turn_progress=20,
    )

    universe.db.save_turn_state(_turn_manager().to_dict())
    universe.db.conn.commit()
    return jsonify({'turn': turn.to_dict()})


@turn_bp.route('/api/turns/<turn_id>/execute', methods=['POST'])
def execute_turn(turn_id):
    universe = _universe()
    turn = _turn_manager().get_turn_by_id(turn_id)
    if not turn:
        return jsonify({'error': 'Turn not found'}), 404

    wrestler = universe.get_wrestler_by_id(turn.wrestler_id)
    if not wrestler:
        return jsonify({'error': 'Wrestler not found'}), 404

    wrestler.alignment = turn.new_alignment.value
    wrestler.adjust_momentum(15 if turn.new_alignment.value == 'Heel' else 10)

    if turn.feud_id:
        feud = universe.feud_manager.get_feud_by_id(turn.feud_id)
        if feud:
            feud.add_segment('office', 'Office Angle', universe.current_year, universe.current_week, 'betrayal',
                             f"{wrestler.name} completed a {turn.new_alignment.value} turn.", intensity_change=18)
            universe.save_feud(feud)

    turn.execute_turn(universe.current_year, universe.current_week, 'office')
    turn.add_segment('office', 'Office Angle', universe.current_year, universe.current_week, 'execution',
                     f"{wrestler.name} turns {turn.new_alignment.value}.",
                     CrowdReaction.HEAT if turn.new_alignment.value == 'Heel' else CrowdReaction.POP,
                     82, 80)

    universe.save_wrestler(wrestler)
    universe.db.save_turn_state(_turn_manager().to_dict())
    universe.db.conn.commit()
    return jsonify({'turn': turn.to_dict(), 'wrestler': wrestler.to_dict()})
