"""
Developmental Routes - API endpoints for ROC Nexus developmental brand
Handles call-ups, roster management, and developmental championship.
"""

from flask import Blueprint, jsonify, request, current_app

developmental_bp = Blueprint('developmental', __name__)


def get_universe():
    """Get the universe state from app config"""
    return current_app.config.get('UNIVERSE')


def get_dev_manager():
    """Get the developmental roster manager from app config"""
    return current_app.config.get('DEV_ROSTER_MANAGER')


def get_call_up_engine():
    """Get the call-up engine from app config"""
    return current_app.config.get('CALL_UP_ENGINE')


# ============================================================================
# DEVELOPMENTAL ROSTER ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/roster', methods=['GET'])
def api_get_developmental_roster():
    """Get all wrestlers on the developmental roster"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entries = dev_manager.get_all_entries()
        
        return jsonify({
            'total': len(entries),
            'ready_for_call_up': len(dev_manager.get_ready_for_call_up()),
            'wrestlers': [entry.to_dict() for entry in entries]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>', methods=['GET'])
def api_get_developmental_wrestler(wrestler_id):
    """Get details for a specific developmental wrestler"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found in developmental roster'}), 404
        
        return jsonify(entry.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/update_performance', methods=['POST'])
def api_update_developmental_performance(wrestler_id):
    """Update performance metrics for a developmental wrestler after a match"""
    try:
        data = request.get_json()
        match_quality = float(data.get('match_quality', 50))
        crowd_reaction = float(data.get('crowd_reaction', 50))
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.update_performance(match_quality, crowd_reaction)
        
        return jsonify({
            'success': True,
            'message': 'Performance updated',
            'updated_stats': {
                'developmental_rating': entry.developmental_rating,
                'match_quality_avg': round(entry.match_quality_avg, 2),
                'crowd_reaction_avg': round(entry.crowd_reaction_avg, 2),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/coaching_notes', methods=['PUT'])
def api_update_coaching_notes(wrestler_id):
    """Update coaching notes for a developmental wrestler"""
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.coaching_notes = notes
        
        return jsonify({
            'success': True,
            'message': 'Coaching notes updated',
            'notes': entry.coaching_notes
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/training_focus', methods=['PUT'])
def api_update_training_focus(wrestler_id):
    """Update training focus areas for a developmental wrestler"""
    try:
        data = request.get_json()
        training_focus = data.get('training_focus', [])
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.training_focus = training_focus
        
        return jsonify({
            'success': True,
            'message': 'Training focus updated',
            'training_focus': entry.training_focus
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/wrestler/<wrestler_id>/achievement', methods=['POST'])
def api_add_achievement(wrestler_id):
    """Add an achievement to a developmental wrestler's record"""
    try:
        data = request.get_json()
        achievement = data.get('achievement', '')
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        entry = dev_manager.get_entry(wrestler_id)
        if not entry:
            return jsonify({'error': 'Wrestler not found'}), 404
        
        entry.add_achievement(achievement)
        
        return jsonify({
            'success': True,
            'message': 'Achievement added',
            'achievements': entry.achievements
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CALL-UP ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/call-up/recommendations', methods=['GET'])
def api_get_call_up_recommendations():
    """Get AI-generated call-up recommendations"""
    try:
        universe = get_universe()
        call_up_engine = get_call_up_engine()
        
        if not call_up_engine:
            return jsonify({'error': 'Call-up engine not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        recommendations = call_up_engine.generate_recommendations(
            universe_state=universe,
            current_year=current_year,
            current_week=current_week
        )
        
        return jsonify({
            'total': len(recommendations),
            'recommendations': [rec.to_dict() for rec in recommendations]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/initiate', methods=['POST'])
def api_initiate_call_up():
    """Initiate a call-up from developmental to main roster"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        destination_brand = data.get('destination_brand')
        reason = data.get('reason', 'brand_need')
        initiating_gm = data.get('initiating_gm')
        
        if not wrestler_id or not destination_brand:
            return jsonify({'error': 'Missing required fields'}), 400
        
        valid_brands = ['ROC Alpha', 'ROC Velocity', 'ROC Vanguard']
        if destination_brand not in valid_brands:
            return jsonify({'error': f'Invalid brand. Must be one of: {valid_brands}'}), 400
        
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager or not call_up_engine:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        # Import CallUpReason enum
        from models.developmental_roster import CallUpReason
        
        try:
            reason_enum = CallUpReason(reason)
        except ValueError:
            return jsonify({'error': f'Invalid reason. Valid reasons: {[r.value for r in CallUpReason]}'}), 400
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        result = call_up_engine.execute_call_up(
            wrestler_id=wrestler_id,
            destination_brand=destination_brand,
            reason=reason_enum,
            universe_state=universe,
            current_year=current_year,
            current_week=current_week,
            initiating_gm=initiating_gm
        )
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/outcome', methods=['POST'])
def api_process_call_up_outcome():
    """Process the outcome of a call-up (success/failure)"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        success = data.get('success', False)
        
        if not wrestler_id:
            return jsonify({'error': 'Missing wrestler_id'}), 400
        
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager or not call_up_engine:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        result = call_up_engine.simulate_call_up_outcome(
            wrestler_id=wrestler_id,
            universe_state=universe
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/call-up/history', methods=['GET'])
def api_get_call_up_history():
    """Get call-up history"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        limit = request.args.get('limit', 20, type=int)
        history = dev_manager.get_recent_call_ups(limit)
        
        return jsonify({
            'total': len(history),
            'history': history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/statistics', methods=['GET'])
def api_get_developmental_statistics():
    """Get overall developmental system statistics"""
    try:
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        stats = dev_manager.get_call_up_statistics()
        
        brand_stats = {}
        if call_up_engine and universe:
            brand_stats = call_up_engine.get_brand_statistics(universe)
        
        return jsonify({
            'overall': stats,
            'by_brand': brand_stats,
            'nexus_championship': dev_manager.nexus_championship.to_dict(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# DEVELOPMENTAL CHAMPIONSHIP ENDPOINTS
# ============================================================================

@developmental_bp.route('/api/developmental/championship', methods=['GET'])
def api_get_nexus_championship():
    """Get the Nexus Championship details"""
    try:
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        return jsonify(dev_manager.nexus_championship.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/championship/crown', methods=['POST'])
def api_crown_nexus_champion():
    """Crown a new Nexus Champion"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        wrestler_name = data.get('wrestler_name')
        
        if not wrestler_id or not wrestler_name:
            return jsonify({'error': 'Missing wrestler_id or wrestler_name'}), 400
        
        dev_manager = get_dev_manager()
        universe = get_universe()
        
        if not dev_manager or not universe:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        # Update championship
        champ = dev_manager.nexus_championship
        champ.current_holder_id = wrestler_id
        champ.current_holder_name = wrestler_name
        champ.won_date_year = current_year
        champ.won_date_week = current_week
        champ.days_held = 0
        champ.defense_count = 0
        
        # Add to history
        champ.history.append({
            'wrestler_id': wrestler_id,
            'wrestler_name': wrestler_name,
            'won_date_year': current_year,
            'won_date_week': current_week,
            'days_held': 0,
        })
        
        # Add achievement to wrestler if in developmental
        entry = dev_manager.get_entry(wrestler_id)
        if entry:
            entry.add_achievement('nexus_champion')
        
        return jsonify({
            'success': True,
            'message': f'{wrestler_name} is the new Nexus Champion!',
            'championship': champ.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@developmental_bp.route('/api/developmental/championship/defense', methods=['POST'])
def api_nexus_championship_defense():
    """Record a championship defense"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        successful = data.get('successful', True)
        
        dev_manager = get_dev_manager()
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        champ = dev_manager.nexus_championship
        
        if champ.current_holder_id != wrestler_id:
            return jsonify({'error': 'Wrestler is not the current champion'}), 400
        
        if successful:
            champ.defense_count += 1
            champ.days_held += 7  # Assume weekly shows
        else:
            # Champion lost - will need to crown new champion separately
            pass
        
        return jsonify({
            'success': True,
            'message': 'Championship defense recorded',
            'defenses': champ.defense_count,
            'days_held': champ.days_held
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WEEKLY PROGRESS ENDPOINT
# ============================================================================

@developmental_bp.route('/api/developmental/update_weekly', methods=['POST'])
def api_update_weekly_progress():
    """Update weekly progress for all developmental wrestlers"""
    try:
        dev_manager = get_dev_manager()
        call_up_engine = get_call_up_engine()
        universe = get_universe()
        
        if not dev_manager:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        # Update developmental progress
        dev_manager.update_weekly_progress(current_year, current_week)
        
        # Update cooldowns
        if call_up_engine:
            call_up_engine.update_cooldowns()
        
        return jsonify({
            'success': True,
            'message': 'Weekly progress updated',
            'developmental_count': len(dev_manager.developmental_roster),
            'ready_for_call_up': len(dev_manager.get_ready_for_call_up())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADD TO DEVELOPMENTAL ENDPOINT
# ============================================================================

@developmental_bp.route('/api/developmental/add', methods=['POST'])
def api_add_to_developmental():
    """Add a wrestler to the developmental roster"""
    try:
        data = request.get_json()
        wrestler_id = data.get('wrestler_id')
        wrestler_name = data.get('wrestler_name')
        initial_rating = data.get('initial_rating', 50)
        coaching_notes = data.get('coaching_notes', '')
        
        if not wrestler_id or not wrestler_name:
            return jsonify({'error': 'Missing required fields'}), 400
        
        dev_manager = get_dev_manager()
        universe = get_universe()
        
        if not dev_manager or not universe:
            return jsonify({'error': 'Developmental system not initialized'}), 500
        
        current_year = getattr(universe, 'current_year', 2024)
        current_week = getattr(universe, 'current_week', 1)
        
        entry = dev_manager.add_to_developmental(
            wrestler_id=wrestler_id,
            wrestler_name=wrestler_name,
            current_year=current_year,
            current_week=current_week,
            initial_rating=initial_rating,
            coaching_notes=coaching_notes
        )
        
        # Update wrestler's brand to Nexus
        wrestler = universe.get_wrestler_by_id(wrestler_id)
        if wrestler:
            from models.developmental_roster import DevelopmentalBrand
            wrestler.primary_brand = DevelopmentalBrand.ROC_NEXUS.value
        
        return jsonify({
            'success': True,
            'message': f'{wrestler_name} added to developmental roster',
            'entry': entry.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
