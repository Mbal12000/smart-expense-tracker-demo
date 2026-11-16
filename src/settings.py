"""Settings: currency, theme, CSV export and data reset."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from components import card, confirm_dialog, section_title
from utils import CURRENCIES

if TYPE_CHECKING:
    from main import ExpenseApp


def build_settings(app: "ExpenseApp") -> ft.Control:
    db = app.db

    def on_currency(e):
        db.set_setting("currency", e.control.value)
        app.currency = e.control.value
        app.toast("Currency updated")
        app.refresh()

    def on_theme(e):
        dark = e.control.value
        db.set_setting("theme", "dark" if dark else "light")
        app.page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
        app.page.update()

    def export(e):
        folder = Path.home() / "Downloads"
        if not folder.exists():
            folder = Path(db.path).parent
        path = folder / f"expenses_{date.today().isoformat()}.csv"
        n = db.export_csv(path)
        app.toast(f"Exported {n} transaction(s) to {path}")

    def reset():
        db.clear_all()
        app.toast("All data cleared")
        app.refresh()

    return ft.Column(
        [
            card(
                ft.Column(
                    [
                        section_title("Preferences"),
                        ft.Dropdown(
                            label="Currency",
                            value=app.currency,
                            options=[ft.DropdownOption(key=k, text=v) for k, v in CURRENCIES.items()],
                            on_select=on_currency,
                            width=320,
                        ),
                        ft.Switch(label="Dark mode", value=app.page.theme_mode == ft.ThemeMode.DARK,
                                  on_change=on_theme),
                    ],
                    spacing=14,
                )
            ),
            card(
                ft.Column(
                    [
                        section_title("Your data"),
                        ft.Text(f"Stored locally on this device: {db.path}", size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT, selectable=True),
                        ft.Row(
                            [
                                ft.OutlinedButton("Export to CSV", icon=ft.Icons.DOWNLOAD, on_click=export),
                                ft.OutlinedButton(
                                    "Load sample data", icon=ft.Icons.DATASET,
                                    on_click=lambda e: (db.load_sample_data(), app.toast("Sample data loaded"),
                                                        app.refresh()),
                                ),
                                ft.TextButton(
                                    "Delete all data", icon=ft.Icons.DELETE_FOREVER,
                                    style=ft.ButtonStyle(color=ft.Colors.ERROR),
                                    on_click=lambda e: confirm_dialog(
                                        app, "Delete everything?",
                                        "This removes all transactions, budgets and savings goals.", reset),
                                ),
                            ],
                            wrap=True,
                        ),
                    ],
                    spacing=12,
                )
            ),
            card(
                ft.Column(
                    [
                        section_title("Money tips for students & young professionals"),
                        ft.Text("• Try the 50/30/20 rule: 50% needs, 30% wants, 20% savings.", size=13),
                        ft.Text("• Build an emergency fund of 3 months' expenses before big purchases.", size=13),
                        ft.Text("• Log expenses the same day — small amounts add up fastest.", size=13),
                        ft.Text("• Review subscriptions every month and cancel what you don't use.", size=13),
                    ],
                    spacing=8,
                )
            ),
        ], # pyright: ignore[reportCallIssue]
        spacing=12,
    )
