"""Budgets: monthly overall limit plus per-category limits with live progress."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from components import card, category_avatar, confirm_dialog, empty_state, section_title
from database import EXPENSE_CATEGORIES, OVERALL, Budget
from utils import EXPENSE_COLOR, money, month_label, parse_amount, progress_color, shift_month

if TYPE_CHECKING:
    from main import ExpenseApp


def pct_used(ratio: float) -> int:
    """Round down so 99.7% doesn't show as 100% while still under budget."""
    return int(ratio * 100)


def build_budgets(app: "ExpenseApp") -> ft.Control:
    db, cur, month = app.db, app.currency, app.month
    budgets = db.list_budgets(month)
    spending = db.spending_by_category(month)
    total_spent = db.month_totals(month)["expense"]

    def spent_for(b: Budget) -> float:
        return total_spent if b.category == OVERALL else spending.get(b.category, 0.0)

    def copy_last_month(e):
        prev = shift_month(month, -1)
        n = db.copy_budgets(prev, month)
        app.toast(f"Copied {n} budget(s) from {month_label(prev)}" if n else f"No new budgets in {month_label(prev)}")
        app.refresh()

    header = card(
        ft.Column(
            [
                section_title(
                    f"Budgets for {month_label(month)}",
                    ft.Row(
                        [
                            ft.TextButton("Copy last month", icon=ft.Icons.CONTENT_COPY, on_click=copy_last_month),
                            ft.FilledButton("Add budget", icon=ft.Icons.ADD,
                                            on_click=lambda e: open_budget_dialog(app, budgets)),
                        ],
                        wrap=True,
                    ),
                ),
                ft.Text(
                    "Set an Overall limit for total monthly spending, then add limits for the categories "
                    "you overspend on. Bars turn amber at 80% and red once you go over.",
                    size=13,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=8,
        )
    )

    if not budgets:
        return ft.Column(
            [header, card(empty_state(ft.Icons.TUNE, "No budgets yet",
                                      "Start with an Overall budget, e.g. what's left after rent and transport."))],
            spacing=12,
        )

    tiles = []
    for b in budgets:
        spent = spent_for(b)
        ratio = spent / b.amount
        remaining = b.amount - spent
        status = (f"{money(remaining, cur)} left" if remaining >= 0 else f"{money(-remaining, cur)} over")
        tiles.append(
            card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                category_avatar(b.category, 36),
                                ft.Column(
                                    [
                                        ft.Text(b.category, weight=ft.FontWeight.W_600),
                                        ft.Text(f"{money(spent, cur)} / {money(b.amount, cur)}", size=12,
                                                color=ft.Colors.ON_SURFACE_VARIANT),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.PopupMenuButton(
                                    items=[
                                        ft.PopupMenuItem(content="Edit", icon=ft.Icons.EDIT,
                                                         on_click=lambda e, b=b: open_budget_dialog(app, budgets, b)),
                                        ft.PopupMenuItem(
                                            content="Delete", icon=ft.Icons.DELETE_OUTLINE,
                                            on_click=lambda e, b=b: confirm_dialog(
                                                app, "Delete budget?", f"Remove the {b.category} budget?",
                                                lambda: (db.delete_budget(b.id), app.refresh()), # pyright: ignore[reportArgumentType]
                                            ),
                                        ),
                                    ]
                                ),
                            ],
                            spacing=10,
                        ),
                        ft.ProgressBar(value=min(ratio, 1), color=progress_color(ratio), bar_height=8,
                                       border_radius=4, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
                        ft.Row(
                            [
                                ft.Text(f"{pct_used(ratio)}% used", size=12, color=progress_color(ratio)),
                                ft.Text(status, size=12,
                                        color=EXPENSE_COLOR if remaining < 0 else ft.Colors.ON_SURFACE_VARIANT),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=10,
                ),
                col={"xs": 12, "sm": 6, "lg": 4},
            )
        )

    unbudgeted = {c: a for c, a in spending.items() if c not in {b.category for b in budgets}}
    extra: list[ft.Control] = []
    if unbudgeted:
        extra.append(
            card(
                ft.Column(
                    [section_title("Spending without a budget")]
                    + [
                        ft.Row([ft.Text(c, size=13, expand=True), ft.Text(money(a, cur), size=13)])
                        for c, a in unbudgeted.items()
                    ], # pyright: ignore[reportArgumentType]
                    spacing=8,
                )
            )
        )

    return ft.Column([header, ft.ResponsiveRow(tiles, spacing=12, run_spacing=12), *extra], spacing=12)


def open_budget_dialog(app: "ExpenseApp", existing: list[Budget], budget: Budget | None = None) -> None:
    page = app.page
    used = {b.category for b in existing}
    choices = [OVERALL] + EXPENSE_CATEGORIES
    if budget is None:
        choices = [c for c in choices if c not in used]
        if not choices:
            app.toast("Every category already has a budget this month")
            return

    category_dd = ft.Dropdown(
        label="Category",
        options=[ft.DropdownOption(key=c, text=c) for c in choices],
        value=budget.category if budget else choices[0],
        disabled=budget is not None,
        expand=True,
    )
    amount_field = ft.TextField(
        label="Monthly limit",
        prefix=ft.Text(f"{app.currency} "),
        value=f"{budget.amount:.2f}" if budget else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )

    def save(e):
        amount = parse_amount(amount_field.value)
        if amount is None:
            amount_field.error = "Enter an amount greater than 0"
            page.update()
            return
        app.db.set_budget(app.month, category_dd.value, amount) # pyright: ignore[reportArgumentType]
        page.pop_dialog()
        app.toast("Budget saved")
        app.refresh()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Edit budget" if budget else "New budget"),
            content=ft.Container(ft.Column([ft.Row([category_dd]), amount_field], tight=True, spacing=14,
                                           horizontal_alignment=ft.CrossAxisAlignment.STRETCH), width=380),
            actions=[ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Save", on_click=save)],
        )
    )
