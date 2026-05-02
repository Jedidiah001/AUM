from flask import Flask

from models.alignment import Alignment, CrowdReaction, TurnManager, TurnType
from models.wrestler import Wrestler
from routes.turn_routes import turn_bp


class DummyDB:
    def save_turn_state(self, _state):
        return None

    class Conn:
        def commit(self):
            return None

    conn = Conn()


class DummyUniverse:
    current_year = 2
    current_week = 10
    feud_manager = None

    def __init__(self, wrestler):
        self._wrestler = wrestler

    def get_wrestler_by_id(self, wrestler_id):
        return self._wrestler if wrestler_id == self._wrestler.id else None


def _make_wrestler(wid="w1", name="Ace", alignment="Face"):
    return Wrestler(
        wrestler_id=wid,
        name=name,
        age=30,
        gender="Male",
        alignment=alignment,
        role="Main Event",
        primary_brand="AWUM",
        brawling=80,
        technical=78,
        speed=75,
        mic=85,
        psychology=83,
        stamina=82,
        years_experience=10,
        is_major_superstar=True,
        popularity=80,
        momentum=70,
        morale=75,
        fatigue=10,
    )


def test_turn_manager_round_trip_and_reaction_tracking():
    manager = TurnManager()
    turn = manager.create_turn(
        wrestler_id="w1",
        wrestler_name="Ace",
        turn_type=TurnType.GRADUAL_TURN,
        old_alignment=Alignment.FACE,
        new_alignment=Alignment.HEEL,
        year=1,
        week=1,
    )

    turn.add_segment(
        show_id="show_1",
        show_name="Dynamite",
        year=1,
        week=2,
        segment_type="promo",
        description="Ace teases frustration with the fans.",
        crowd_reaction=CrowdReaction.MIXED,
        crowd_heat_level=55,
        turn_progress=45,
    )

    payload = manager.to_dict()
    loaded = TurnManager()
    loaded.load_from_dict(payload)

    restored = loaded.get_turn_by_id(turn.id)
    assert restored is not None
    assert restored.turn_progress == 45
    assert restored.phase.value == "buildup"
    assert restored.crowd_history is not None


def test_execute_turn_endpoint_uses_engine_not_manager_method():
    app = Flask(__name__)
    app.register_blueprint(turn_bp)

    wrestler = _make_wrestler()
    manager = TurnManager()
    turn = manager.create_turn(
        wrestler_id=wrestler.id,
        wrestler_name=wrestler.name,
        turn_type=TurnType.GRADUAL_TURN,
        old_alignment=Alignment.FACE,
        new_alignment=Alignment.HEEL,
        year=1,
        week=1,
    )

    app.config["DATABASE"] = DummyDB()
    app.config["UNIVERSE"] = DummyUniverse(wrestler)
    app.config["TURN_MANAGER"] = manager

    client = app.test_client()
    resp = client.post(f"/api/turns/{turn.id}/execute", json={"show_id": "show_2"})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True
    assert data["turn"]["phase"] == "execution"
