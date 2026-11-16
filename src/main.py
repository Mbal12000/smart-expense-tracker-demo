"""Smart Expense Tracker — a Flet app that helps students and young professionals
track spending, set monthly budgets and monitor savings.

Run with:  flet run        (desktop)
           flet run --web  (browser)
"""

from __future__ import annotations

import flet as ft
import tempfile
import uuid
from pathlib import Path

from components import open_transaction_dialog
from database import Database
from utils import current_month, month_label, shift_month
from budgets import build_budgets
from dashboard import build_dashboard
from savings import build_savings
from settings import build_settings
from transactions import build_transactions

APP_NAME = "Smart Expense Tracker"
SEED = ft.Colors.TEAL

# (label, icon, selected icon, builder, uses month selector)
TABS = [
    ("Home", ft.Icons.DASHBOARD_OUTLINED, ft.Icons.DASHBOARD, build_dashboard, True),
    ("Transactions", ft.Icons.RECEIPT_LONG_OUTLINED, ft.Icons.RECEIPT_LONG, build_transactions, True),
    ("Budgets", ft.Icons.PIE_CHART_OUTLINE, ft.Icons.PIE_CHART, build_budgets, True),
    ("Savings", ft.Icons.SAVINGS_OUTLINED, ft.Icons.SAVINGS, build_savings, False),
    ("Settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS, build_settings, False),
]


class ExpenseApp:
    def __init__(self, page: ft.Page, db: Database | None = None):
        self.page = page
        self.db = db or Database()
        self.month = current_month()
        self.currency = self.db.get_setting("currency", "R")
        self.tab = 0
        self.view_state: dict = {}  # per-view UI state (filters etc.) kept between refreshes

        page.title = APP_NAME
        page.theme = ft.Theme(color_scheme_seed=SEED)
        page.dark_theme = ft.Theme(color_scheme_seed=SEED)
        page.theme_mode = ft.ThemeMode.DARK if self.db.get_setting("theme") == "dark" else ft.ThemeMode.LIGHT
        page.padding = 0
        page.window.min_width = 380
        page.window.width = 1100
        page.window.height = 800

        self.month_text = ft.Text(weight=ft.FontWeight.W_600)
        self.month_selector = ft.Row(
            [
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Previous month", on_click=lambda e: self.change_month(-1)),
                self.month_text,
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Next month", on_click=lambda e: self.change_month(1)),
            ],
            spacing=0,
        )
        self.title_text = ft.Text(APP_NAME, weight=ft.FontWeight.BOLD)
        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.PRIMARY),
            leading_width=48,
            title=self.title_text,
            actions=[self.month_selector, ft.Container(width=8)],
        )
        page.navigation_bar = ft.NavigationBar(
            destinations=[ft.NavigationBarDestination(icon=i, selected_icon=si, label=l) for l, i, si, _, _ in TABS],
            on_change=lambda e: self.go(e.control.selected_index),
        )
        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            tooltip="Add expense",
            on_click=lambda e: open_transaction_dialog(self, self.refresh),
        )
        self.body = ft.Container(padding=16, expand=True)
        page.add(
            ft.Column(
                [self.body],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )
        self.refresh()

    # ------------------------------------------------------------ navigation
    def go(self, index: int) -> None:
        self.tab = index
        assert self.page.navigation_bar is not None
        self.page.navigation_bar.selected_index = index
        self.refresh()

    def change_month(self, delta: int) -> None:
        nxt = shift_month(self.month, delta)
        if nxt > current_month():
            self.toast("You can't view future months yet")
            return
        self.month = nxt
        self.refresh()

    def refresh(self) -> None:
        label, _, _, builder, monthly = TABS[self.tab]
        self.title_text.value = APP_NAME if self.tab == 0 else label
        self.month_selector.visible = monthly
        self.month_text.value = month_label(self.month)
        assert self.page.floating_action_button is not None
        self.page.floating_action_button.visible = self.tab in (0, 1)
        self.body.content = builder(self)
        self.page.update()

    def toast(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(message), duration=2500))


def main(page: ft.Page):
    # Each browser session receives its own temporary database. This prevents
    # public demo visitors from seeing or changing one another's financial data.
    # Render's free filesystem is ephemeral, so demo changes reset on restart.
    demo_db = Path(tempfile.gettempdir()) / f"expense_tracker_demo_{uuid.uuid4().hex}.db"
    db = Database(demo_db)
    db.load_sample_data()
    ExpenseApp(page, db=db)


if __name__ == "__main__":
    ft.run(main)
