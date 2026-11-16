"""Run with:  python -m pytest tests -q   (from the project root)"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from database import OVERALL, Database  # noqa: E402
from utils import current_month, parse_amount, shift_month  # noqa: E402
from budgets import build_budgets  # noqa: E402
from dashboard import build_dashboard  # noqa: E402
from savings import build_savings  # noqa: E402
from settings import build_settings  # noqa: E402
from transactions import build_transactions  # noqa: E402


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    yield d
    d.close()


class FakeApp:
    def __init__(self, db):
        self.db = db
        self.page = MagicMock()
        self.month = current_month()
        self.currency = "R"
        self.view_state = {}

    def refresh(self):
        pass

    def toast(self, msg):
        pass

    def go(self, i):
        pass


def test_parse_amount():
    assert parse_amount("1 250,50") == 1250.50
    assert parse_amount("1,250.50") == 1250.50
    assert parse_amount("45") == 45
    assert parse_amount("-3") is None
    assert parse_amount("abc") is None
    assert parse_amount("") is None


def test_shift_month():
    assert shift_month("2026-01", -1) == "2025-12"
    assert shift_month("2026-12", 1) == "2027-01"
    assert shift_month("2026-05", 0) == "2026-05"


def test_transactions_and_totals(db):
    m = current_month()
    db.add_transaction("income", 5000, "Salary", "", f"{m}-01")
    db.add_transaction("expense", 300, "Transport", "taxi", f"{m}-01")
    db.add_transaction("expense", 200, "Transport", "bus", f"{m}-01")
    db.add_transaction("expense", 100, "Food & Groceries", "", f"{m}-01")
    assert db.month_totals(m) == {"income": 5000, "expense": 600}
    assert db.spending_by_category(m) == {"Transport": 500, "Food & Groceries": 100}
    assert len(db.list_transactions(month=m, kind="expense")) == 3
    assert len(db.list_transactions(search="taxi")) == 1


def test_budgets_upsert_and_copy(db):
    m = current_month()
    prev = shift_month(m, -1)
    db.set_budget(prev, OVERALL, 4000)
    db.set_budget(prev, "Transport", 500)
    db.set_budget(m, "Transport", 600)
    assert db.copy_budgets(prev, m) == 1  # Transport already exists, not overwritten
    budgets = {b.category: b.amount for b in db.list_budgets(m)}
    assert budgets == {OVERALL: 4000, "Transport": 600}
    assert db.list_budgets(m)[0].category == OVERALL


def test_goal_contributions_never_negative(db):
    g = db.add_goal("Laptop", 8000, None)
    db.contribute_to_goal(g, 1000)
    db.contribute_to_goal(g, -5000)
    assert db.list_goals()[0].saved == 0
    assert db.total_saved() == 0


def test_csv_export(db, tmp_path):
    db.load_sample_data()
    out = tmp_path / "out.csv"
    n = db.export_csv(out)
    assert n == len(db.list_transactions())
    assert out.read_text().startswith("date,type,category,amount,note")


@pytest.mark.parametrize("sample", [False, True])
def test_all_views_build(db, sample):
    if sample:
        db.load_sample_data()
    app = FakeApp(db)
    for builder in (build_dashboard, build_transactions, build_budgets, build_savings, build_settings):
        assert builder(app) is not None
