import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
from models.tables import Position
from services.position_manager import PositionManager
from config import get_settings

settings = get_settings()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def pm():
    return PositionManager()


class TestTrailingStopLoss:
    def test_stop_loss_initial(self, db, pm):
        """Stop loss set at 5% below entry."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)
        assert pos.stop_loss == 285.0
        assert pos.base_price == 300.0

    def test_milestone_trigger_at_10pct(self, db, pm):
        """When price rises 10%, SL moves up to lock 5% profit."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # Price rises to 330 (+10%)
        result = pm.update_price(db, pos, 330.0)
        assert result["action"] == "milestone"
        assert pos.stop_loss == 313.5  # 330 * 0.95
        assert pos.milestone_count == 1

    def test_multiple_milestones(self, db, pm):
        """Multiple milestone triggers compound correctly."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # First milestone: 330 (+10%)
        pm.update_price(db, pos, 330.0)
        assert pos.stop_loss == 313.5
        assert pos.milestone_count == 1

        # Need to update base to new_base (313.5), then 10% above that
        # Next trigger: 313.5 * 1.10 = 344.85
        pm.update_price(db, pos, 345.0)
        assert pos.milestone_count == 2
        assert pos.stop_loss == pytest.approx(327.75, abs=0.1)

    def test_stop_loss_hit_closes_position(self, db, pm):
        """When price drops to SL, position is closed."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # Price rises to trigger milestone
        pm.update_price(db, pos, 330.0)
        sl = pos.stop_loss  # 313.5

        # Price drops to SL
        result = pm.update_price(db, pos, 310.0)
        assert result["action"] == "stop_loss_hit"
        assert pos.status == "CLOSED"

    def test_stop_loss_guarantees_profit_after_milestone(self, db, pm):
        """After first milestone, stop loss guarantees profit."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # Trigger milestone
        pm.update_price(db, pos, 330.0)

        # SL is at 313.5, which is above entry of 300
        assert pos.stop_loss > pos.entry_price
        profit_per_share = pos.stop_loss - pos.entry_price
        assert profit_per_share > 0

    def test_stop_loss_warning(self, db, pm):
        """Warning when price approaches stop loss."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # Price near SL (within 1%)
        result = pm.update_price(db, pos, 287.5)
        assert result["action"] == "stop_loss_warning"

    def test_hard_stop_loss(self, db, pm):
        """Hard stop at -10% auto-exits."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        # Drop 10% from entry
        result = pm.update_price(db, pos, 270.0)
        assert result["action"] == "stop_loss_hit"
        assert pos.status == "CLOSED"

    def test_no_action_on_normal_price(self, db, pm):
        """No action when price moves normally."""
        pos = pm.open_position(db, "NABIL", 300.0, 10, 0.05)

        result = pm.update_price(db, pos, 310.0)
        assert result["action"] == "none"
        assert pos.status == "OPEN"
