"""Dashboard: month overview, budget health, category breakdown, trend and insights."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from components import card, category_avatar, empty_state, open_transaction_dialog, section_title, stat_card, transaction_tile
from database import OVERALL
from utils import (
    EXPENSE_COLOR, INCOME_COLOR, WARNING_COLOR, days_left_in_month, money, month_label, progress_color, shift_month,
)

if TYPE_CHECKING:
    from main import ExpenseApp


def build_dashboard(app: "ExpenseApp") -> ft.Control:
    db, cur, month = app.db, app.currency, app.month
    totals = db.month_totals(month)
    income, spent = totals["income"], totals["expense"]
    balance = income - spent
    savings_rate = (balance / income * 100) if income else 0
    by_cat = db.spending_by_category(month)
    budgets = {b.category: b.amount for b in db.list_budgets(month)}

    if db.is_empty():
        return ft.Column(
            [
                card(
                    empty_state(
                        ft.Icons.SAVINGS_OUTLINED,
                        "Welcome to Smart Expense Tracker",
                        "Log your first expense or income to start seeing where your money goes.\n"
                        "Want to look around first? Load some sample data.",
                        ft.Row(
                            [
                                ft.FilledButton("Add transaction", icon=ft.Icons.ADD,
                                                on_click=lambda e: open_transaction_dialog(app, app.refresh)),
                                ft.OutlinedButton("Load sample data", icon=ft.Icons.DATASET,
                                                  on_click=lambda e: _load_sample(app)),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            wrap=True,
                        ),
                    )
                )
            ]
        )

    stats = ft.ResponsiveRow(
        [
            stat_card("Income", money(income, cur), ft.Icons.ARROW_DOWNWARD, INCOME_COLOR,
                      hint=month_label(month)),
            stat_card("Spent", money(spent, cur), ft.Icons.ARROW_UPWARD, EXPENSE_COLOR,
                      hint=f"{int(spent / budgets[OVERALL] * 100)}% of budget" if budgets.get(OVERALL) else month_label(month)),
            stat_card("Left over", money(balance, cur), ft.Icons.ACCOUNT_BALANCE_WALLET,
                      INCOME_COLOR if balance >= 0 else EXPENSE_COLOR,
                      hint=f"{savings_rate:.0f}% of income" if income else "No income logged"),
            stat_card("In savings goals", money(db.total_saved(), cur), ft.Icons.SAVINGS, ft.Colors.BLUE,
                      hint=f"Across {len(db.list_goals())} goal(s)"),
        ],
        spacing=12,
        run_spacing=12,
    )

    return ft.Column(
        [
            stats,
            ft.ResponsiveRow(
                [
                    _budget_health(app, spent, budgets.get(OVERALL)),
                    _insights(app, income, spent, by_cat, budgets),
                ],
                spacing=12,
                run_spacing=12,
            ),
            ft.ResponsiveRow(
                [_category_breakdown(app, by_cat, spent), _trend(app)],
                spacing=12,
                run_spacing=12,
            ),
            _recent(app),
        ],
        spacing=12,
    )


def _load_sample(app: "ExpenseApp") -> None:
    app.db.load_sample_data()
    app.toast("Sample data loaded")
    app.refresh()


def _budget_health(app: "ExpenseApp", spent: float, limit: float | None) -> ft.Container:
    cur = app.currency
    if not limit:
        body = ft.Column(
            [
                ft.Text("No overall budget set for this month.", color=ft.Colors.ON_SURFACE_VARIANT),
                ft.OutlinedButton("Set a budget", icon=ft.Icons.TUNE, on_click=lambda e: app.go(2)),
            ], # pyright: ignore[reportCallIssue]
            spacing=10,
        )
    else:
        ratio = spent / limit
        remaining = limit - spent
        days = days_left_in_month(app.month)
        per_day = remaining / days if days and remaining > 0 else 0
        lines = [
            ft.Row(
                [
                    ft.Text(f"{money(spent, cur)} of {money(limit, cur)}", weight=ft.FontWeight.W_600),
                    ft.Text(f"{int(ratio * 100)}%", color=progress_color(ratio), weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.ProgressBar(value=min(ratio, 1), color=progress_color(ratio),
                           bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST, bar_height=10, border_radius=5),
        ]
        if remaining >= 0:
            lines.append(ft.Text(f"{money(remaining, cur)} left to spend", color=ft.Colors.ON_SURFACE_VARIANT))
            if days:
                lines.append(ft.Text(f"≈ {money(per_day, cur)} per day for the next {days} day(s)",
                                     size=13, color=ft.Colors.ON_SURFACE_VARIANT))
        else:
            lines.append(ft.Text(f"Over budget by {money(-remaining, cur)}", color=EXPENSE_COLOR,
                                 weight=ft.FontWeight.W_600))
        body = ft.Column(lines, spacing=10)

    return card(ft.Column([section_title("Monthly budget"), body], spacing=12), col={"xs": 12, "md": 6})


def _insights(app: "ExpenseApp", income: float, spent: float, by_cat: dict, budgets: dict) -> ft.Container:
    cur = app.currency
    tips: list[tuple[ft.IconData, str, str]] = []

    over = [c for c, amt in by_cat.items() if c in budgets and amt > budgets[c]]
    near = [c for c, amt in by_cat.items() if c in budgets and 0.8 * budgets[c] <= amt <= budgets[c]]
    for c in over:
        tips.append((ft.Icons.ERROR_OUTLINE, f"You've gone over your {c} budget.", EXPENSE_COLOR))
    for c in near:
        tips.append((ft.Icons.WARNING_AMBER, f"{c} is above 80% of its budget.", WARNING_COLOR))

    if by_cat:
        top_cat, top_amt = next(iter(by_cat.items()))
        share = top_amt / spent * 100 if spent else 0
        tips.append((ft.Icons.PIE_CHART_OUTLINE, f"{top_cat} is your biggest expense ({share:.0f}% of spending).",
                     ft.Colors.BLUE))

    prev = app.db.month_totals(shift_month(app.month, -1))["expense"]
    if prev and spent:
        diff = (spent - prev) / prev * 100
        if abs(diff) >= 5:
            word = "more" if diff > 0 else "less"
            tips.append((ft.Icons.TRENDING_UP if diff > 0 else ft.Icons.TRENDING_DOWN,
                         f"You've spent {abs(diff):.0f}% {word} than last month.",
                         EXPENSE_COLOR if diff > 0 else INCOME_COLOR))

    if income:
        rate = (income - spent) / income * 100
        if rate >= 20:
            tips.append((ft.Icons.EMOJI_EVENTS, f"Great job — you're keeping {rate:.0f}% of your income.", INCOME_COLOR))
        elif rate > 0:
            target = income * 0.2 - (income - spent)
            tips.append((ft.Icons.LIGHTBULB_OUTLINE,
                         f"Trim {money(target, cur)} to hit the 20% savings rule of thumb.", WARNING_COLOR))
        else:
            tips.append((ft.Icons.LIGHTBULB_OUTLINE, "You're spending more than you earn this month.", EXPENSE_COLOR))

    if not tips:
        tips.append((ft.Icons.INFO_OUTLINE, "Add more transactions and budgets to get personalised tips.",
                     ft.Colors.ON_SURFACE_VARIANT))

    rows = [
        ft.Row([ft.Icon(icon, color=color, size=20), ft.Text(text, expand=True, size=13)], spacing=10,
               vertical_alignment=ft.CrossAxisAlignment.START)
        for icon, text, color in tips[:5]
    ]
    return card(ft.Column([section_title("Smart insights"), *rows], spacing=12), col={"xs": 12, "md": 6})


def _category_breakdown(app: "ExpenseApp", by_cat: dict, spent: float) -> ft.Container:
    cur = app.currency
    if not by_cat:
        body: list[ft.Control] = [ft.Text("No spending recorded this month.", color=ft.Colors.ON_SURFACE_VARIANT)]
    else:
        body = []
        for cat, amt in list(by_cat.items())[:6]:
            share = amt / spent if spent else 0
            body.append(
                ft.Row(
                    [
                        category_avatar(cat, 34),
                        ft.Column(
                            [
                                ft.Row(
                                    [ft.Text(cat, size=13, expand=True), ft.Text(money(amt, cur), size=13,
                                                                                weight=ft.FontWeight.W_500)],
                                ),
                                ft.ProgressBar(value=share, bar_height=6, border_radius=3,
                                               bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                )
            )
    return card(ft.Column([section_title("Where your money went"), *body], spacing=12), col={"xs": 12, "md": 6})


def _trend(app: "ExpenseApp") -> ft.Container:
    """Simple six-month income vs spending bar chart built from containers."""
    months = [shift_month(app.month, -i) for i in range(5, -1, -1)]
    history = app.db.monthly_history(months)
    peak = max([max(h["income"], h["expense"]) for h in history] + [1])
    chart_h = 140

    def bar(value: float, color: str) -> ft.Container:
        return ft.Container(width=12, height=max(2, value / peak * chart_h), bgcolor=color,
                            border_radius=ft.BorderRadius.only(top_left=4, top_right=4),
                            tooltip=money(value, app.currency))

    columns = [
        ft.Column(
            [
                ft.Row([bar(h["income"], INCOME_COLOR), bar(h["expense"], EXPENSE_COLOR)], spacing=3,
                       vertical_alignment=ft.CrossAxisAlignment.END, height=chart_h),
                ft.Text(month_label(h["month"], short=True)[:3], size=11, color=ft.Colors.ON_SURFACE_VARIANT,
                        weight=ft.FontWeight.BOLD if h["month"] == app.month else None),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        )
        for h in history
    ]
    legend = ft.Row(
        [
            ft.Container(width=10, height=10, bgcolor=INCOME_COLOR, border_radius=2), ft.Text("Income", size=12),
            ft.Container(width=10, height=10, bgcolor=EXPENSE_COLOR, border_radius=2), ft.Text("Spending", size=12),
        ],
        spacing=6,
    )
    return card(
        ft.Column(
            [section_title("6-month trend", legend),
             ft.Row(columns, alignment=ft.MainAxisAlignment.SPACE_AROUND, # pyright: ignore[reportArgumentType]
                    vertical_alignment=ft.CrossAxisAlignment.END)],
            spacing=16,
        ),
        col={"xs": 12, "md": 6},
    )


def _recent(app: "ExpenseApp") -> ft.Container:
    txs = app.db.list_transactions(month=app.month, limit=5)
    body: list[ft.Control] = (
        [transaction_tile(app, t, app.refresh) for t in txs]
        if txs
        else [ft.Text(f"Nothing logged in {month_label(app.month)} yet.", color=ft.Colors.ON_SURFACE_VARIANT)]
    )
    return card(
        ft.Column(
            [section_title("Recent transactions", ft.TextButton("See all", on_click=lambda e: app.go(1))), *body],
            spacing=4,
        )
    )
