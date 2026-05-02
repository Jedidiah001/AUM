from models.alignment import Alignment, CrowdReaction, TurnType, TurnManager
from simulation.turn_booking import TurnBookingEngine


class DummyStats:
    popularity = 60


class DummyWrestler:
    def __init__(self):
        self.id = 'w1'
        self.name = 'Test'
        self.alignment = 'Face'
        self.stats = DummyStats()
        self.pop_shift = 0

    def adjust_popularity(self, delta):
        self.pop_shift += delta


class DummyFeudMgr:
    def get_feud_by_id(self, _):
        return None


class DummyUniverse:
    current_year = 1
    current_week = 1
    feud_manager = DummyFeudMgr()

    def __init__(self):
        self.w = DummyWrestler()

    def get_wrestler_by_id(self, _):
        return self.w

    def save_wrestler(self, _):
        pass

    def save_feud(self, _):
        pass


def test_turn_progresses_and_resolves():
    u = DummyUniverse()
    tm = TurnManager()
    turn = tm.create_turn('w1', 'Test', TurnType.GRADUAL_TURN, Alignment.FACE, Alignment.HEEL, 1, 1)
    engine = TurnBookingEngine(u)
    for _ in range(8):
        engine.advance_turn(turn, 's1', 'Show', 'attack', CrowdReaction.HEAT)
        if turn.is_completed:
            break
    assert turn.is_completed
    assert u.w.alignment == 'Heel'


def test_immediate_turn_executes_and_persists_alignment():
    u = DummyUniverse()
    tm = TurnManager()
    turn = tm.create_turn('w1', 'Test', TurnType.SUDDEN_BETRAYAL, Alignment.FACE, Alignment.HEEL, 1, 1)
    engine = TurnBookingEngine(u)
    result = engine.execute_immediate_turn(turn, 's1', 'Show', CrowdReaction.HEAT)
    assert result['turn']['is_completed'] is True
    assert u.w.alignment == 'Heel'
