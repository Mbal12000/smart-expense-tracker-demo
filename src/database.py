"""SQLite data layer for Smart Expense Tracker.

All money values are stored as REAL in the user's chosen currency.
Dates are stored as ISO strings (YYYY-MM-DD); months as YYYY-MM.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

EXPENSE_CATEGORIES = [
    "Food & Groceries",
    "Transport",
    "Rent & Housing",
    "Utilities",
    "Data & Airtime",
    "Education",
    "Entertainment",
    "Shopping",
    "Health",
    "Personal Care",
    "Subscriptions",
    "Gifts & Donations",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Allowance",
    "Bursary / Scholarship",
    "Side Hustle",
    "Freelance",
    "Gift",
    "Other Income",
]

OVERALL = "Overall"  # special budget category = total monthly spending limit


def default_db_path() -> Path:
    """Use Flet's app storage dir when packaged, otherwise a folder in $HOME."""
    base = os.getenv("FLET_APP_STORAGE_DATA")
    folder = Path(base) if base else Path.home() / ".smart_expense_tracker"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "expenses.db"


@dataclass
class Transaction:
    id: int
    kind: str  # "expense" | "income"
    amount: float
    category: str
    note: str
    date: str


@dataclass
class Budget:
    id: int
    month: str
    category: str
    amount: float


@dataclass
class SavingsGoal:
    id: int
    name: str
    target: float
    saved: float
    deadline: str | None


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = str(path or default_db_path())
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    # ------------------------------------------------------------------ setup
    def _create_tables(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK (kind IN ('expense', 'income')),
                amount REAL NOT NULL CHECK (amount > 0),
                category TEXT NOT NULL,
                note TEXT DEFAULT '',
                date TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                UNIQUE (month, category)
            );

            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target REAL NOT NULL CHECK (target > 0),
                saved REAL NOT NULL DEFAULT 0,
                deadline TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # --------------------------------------------------------------- settings
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    # ----------------------------------------------------------- transactions
    def add_transaction(self, kind: str, amount: float, category: str, note: str, on: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO transactions(kind, amount, category, note, date) VALUES(?,?,?,?,?)",
            (kind, amount, category, note.strip(), on),
        )
        self.conn.commit()
        return cur.lastrowid # pyright: ignore[reportReturnType]

    def update_transaction(self, tx_id: int, kind: str, amount: float, category: str, note: str, on: str) -> None:
        self.conn.execute(
            "UPDATE transactions SET kind=?, amount=?, category=?, note=?, date=? WHERE id=?",
            (kind, amount, category, note.strip(), on, tx_id),
        )
        self.conn.commit()

    def delete_transaction(self, tx_id: int) -> None:
        self.conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
        self.conn.commit()

    def list_transactions(
        self, month: str | None = None, kind: str | None = None, search: str = "", limit: int | None = None
    ) -> list[Transaction]:
        sql = "SELECT * FROM transactions WHERE 1=1"
        args: list = []
        if month:
            sql += " AND substr(date, 1, 7) = ?"
            args.append(month)
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        if search:
            sql += " AND (note LIKE ? OR category LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        sql += " ORDER BY date DESC, id DESC"
        if limit:
            sql += " LIMIT ?"
            args.append(limit)
        return [Transaction(**dict(r)) for r in self.conn.execute(sql, args)]

    def month_totals(self, month: str) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT kind, COALESCE(SUM(amount), 0) AS total FROM transactions "
            "WHERE substr(date, 1, 7) = ? GROUP BY kind",
            (month,),
        ).fetchall()
        totals = {"income": 0.0, "expense": 0.0}
        for r in rows:
            totals[r["kind"]] = r["total"]
        return totals

    def spending_by_category(self, month: str) -> dict[str, float]:
        rows = self.conn.execute(
            "SELECT category, SUM(amount) AS total FROM transactions "
            "WHERE kind='expense' AND substr(date, 1, 7) = ? "
            "GROUP BY category ORDER BY total DESC",
            (month,),
        ).fetchall()
        return {r["category"]: r["total"] for r in rows}

    def monthly_history(self, months: list[str]) -> list[dict]:
        """Income/expense totals for each month in `months` (in given order)."""
        return [{"month": m, **self.month_totals(m)} for m in months]

    # ---------------------------------------------------------------- budgets
    def set_budget(self, month: str, category: str, amount: float) -> None:
        self.conn.execute(
            "INSERT INTO budgets(month, category, amount) VALUES(?,?,?) "
            "ON CONFLICT(month, category) DO UPDATE SET amount=excluded.amount",
            (month, category, amount),
        )
        self.conn.commit()

    def delete_budget(self, budget_id: int) -> None:
        self.conn.execute("DELETE FROM budgets WHERE id=?", (budget_id,))
        self.conn.commit()

    def list_budgets(self, month: str) -> list[Budget]:
        rows = self.conn.execute(
            "SELECT * FROM budgets WHERE month=? "
            "ORDER BY CASE WHEN category=? THEN 0 ELSE 1 END, category",
            (month, OVERALL),
        )
        return [Budget(**dict(r)) for r in rows]

    def copy_budgets(self, from_month: str, to_month: str) -> int:
        """Copy budgets from one month to another without overwriting existing ones."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO budgets(month, category, amount) "
            "SELECT ?, category, amount FROM budgets WHERE month=?",
            (to_month, from_month),
        )
        self.conn.commit()
        return cur.rowcount

    # ---------------------------------------------------------- savings goals
    def add_goal(self, name: str, target: float, deadline: str | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO savings_goals(name, target, deadline) VALUES(?,?,?)",
            (name.strip(), target, deadline),
        )
        self.conn.commit()
        return cur.lastrowid # pyright: ignore[reportReturnType]

    def update_goal(self, goal_id: int, name: str, target: float, deadline: str | None) -> None:
        self.conn.execute(
            "UPDATE savings_goals SET name=?, target=?, deadline=? WHERE id=?",
            (name.strip(), target, deadline, goal_id),
        )
        self.conn.commit()

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        """Positive amount = deposit, negative = withdrawal. Never goes below 0."""
        self.conn.execute(
            "UPDATE savings_goals SET saved = MAX(0, saved + ?) WHERE id=?",
            (amount, goal_id),
        )
        self.conn.commit()

    def delete_goal(self, goal_id: int) -> None:
        self.conn.execute("DELETE FROM savings_goals WHERE id=?", (goal_id,))
        self.conn.commit()

    def list_goals(self) -> list[SavingsGoal]:
        rows = self.conn.execute(
            "SELECT * FROM savings_goals ORDER BY (saved >= target), deadline IS NULL, deadline, id"
        )
        return [SavingsGoal(**dict(r)) for r in rows]

    def total_saved(self) -> float:
        row = self.conn.execute("SELECT COALESCE(SUM(saved), 0) AS s FROM savings_goals").fetchone()
        return row["s"]

    # ------------------------------------------------------------- utilities
    def is_empty(self) -> bool:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()
        return row["n"] == 0

    def export_csv(self, path: str | Path) -> int:
        import csv

        txs = self.list_transactions()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["date", "type", "category", "amount", "note"])
            for t in txs:
                writer.writerow([t.date, t.kind, t.category, f"{t.amount:.2f}", t.note])
        return len(txs)

    def clear_all(self) -> None:
        self.conn.executescript(
            "DELETE FROM transactions; DELETE FROM budgets; DELETE FROM savings_goals;"
        )
        self.conn.commit()

    def load_sample_data(self) -> None:
        """Seed a realistic month of data so new users can explore the app."""
        today = date.today()
        m = today.strftime("%Y-%m")
        day = lambda d: f"{m}-{min(d, today.day):02d}"  # never in the future
        samples = [
            ("income", 6500, "Salary", "Part-time job", 1),
            ("income", 1200, "Side Hustle", "Tutoring", 3),
            ("expense", 2800, "Rent & Housing", "Room rent", 1),
            ("expense", 450, "Transport", "Taxi fare - monthly", 2),
            ("expense", 299, "Data & Airtime", "Monthly data bundle", 2),
            ("expense", 620, "Food & Groceries", "Groceries", 4),
            ("expense", 85, "Food & Groceries", "Lunch with friends", 5),
            ("expense", 159, "Subscriptions", "Music + streaming", 6),
            ("expense", 350, "Education", "Textbook", 7),
            ("expense", 180, "Entertainment", "Movie night", 8),
        ]
        for kind, amount, cat, note, d in samples:
            self.add_transaction(kind, amount, cat, note, day(d))
        self.set_budget(m, OVERALL, 5500)
        self.set_budget(m, "Food & Groceries", 1200)
        self.set_budget(m, "Transport", 500)
        self.set_budget(m, "Entertainment", 300)
        self.set_budget(m, "Data & Airtime", 300)
        g1 = self.add_goal("Emergency fund", 5000, None)
        self.contribute_to_goal(g1, 1500)
        g2 = self.add_goal("New laptop", 9000, f"{today.year + 1}-01-31")
        self.contribute_to_goal(g2, 2200)
