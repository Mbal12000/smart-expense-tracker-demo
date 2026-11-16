"""Savings goals: targets, deposits/withdrawals and a monthly amount needed to stay on track."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from components import card, confirm_dialog, empty_state, section_title, stat_card
from database import SavingsGoal
from utils import INCOME_COLOR, money, parse_amount

if TYPE_CHECKING:
    from main import ExpenseApp


def _months_until(deadline: str) -> int:
    d, today = date.fromisoformat(deadline), date.today()
    return max(0, (d.year - today.year) * 12 + (d.month - today.month))


def build_savings(app: "ExpenseApp") -> ft.Control:
    db, cur = app.db, app.currency
    goals = db.list_goals()
    total_saved = sum(g.saved for g in goals)
    total_target = sum(g.target for g in goals)

    header = ft.ResponsiveRow(
        [
            stat_card("Total saved", money(total_saved, cur), ft.Icons.SAVINGS, INCOME_COLOR, col={"xs": 6, "md": 4}),
            stat_card("Total targets", money(total_target, cur), ft.Icons.FLAG, ft.Colors.BLUE, col={"xs": 6, "md": 4}),
            stat_card("Goals completed", f"{sum(g.saved >= g.target for g in goals)} / {len(goals)}",
                      ft.Icons.EMOJI_EVENTS, ft.Colors.AMBER, col={"xs": 12, "md": 4}),
        ],
        spacing=12,
        run_spacing=12,
    )
    toolbar = section_title(
        "Your goals",
        ft.FilledButton("New goal", icon=ft.Icons.ADD, on_click=lambda e: open_goal_dialog(app)),
    )

    if not goals:
        return ft.Column(
            [header, toolbar,
             card(empty_state(ft.Icons.SAVINGS_OUTLINED, "No savings goals yet",
                              "Create a goal like an emergency fund, a laptop, or next year's fees."))],
            spacing=12,
        )

    tiles = [_goal_card(app, g) for g in goals]
    return ft.Column([header, toolbar, ft.ResponsiveRow(tiles, spacing=12, run_spacing=12)], spacing=12) # pyright: ignore[reportArgumentType]


def _goal_card(app: "ExpenseApp", g: SavingsGoal) -> ft.Container:
    cur = app.currency
    ratio = g.saved / g.target
    done = ratio >= 1
    remaining = max(0.0, g.target - g.saved)

    details: list[ft.Control] = []
    if done:
        details.append(ft.Text("Goal reached! 🎉", color=INCOME_COLOR, weight=ft.FontWeight.W_600))
    elif g.deadline:
        months = _months_until(g.deadline)
        deadline_txt = date.fromisoformat(g.deadline).strftime("%d %b %Y")
        if date.fromisoformat(g.deadline) < date.today():
            details.append(ft.Text(f"Deadline passed ({deadline_txt})", size=12, color=ft.Colors.ERROR))
        else:
            per_month = remaining / max(1, months)
            details.append(ft.Text(f"Save {money(per_month, cur)}/month to reach it by {deadline_txt}", size=12,
                                   color=ft.Colors.ON_SURFACE_VARIANT))
    else:
        details.append(ft.Text(f"{money(remaining, cur)} to go", size=12, color=ft.Colors.ON_SURFACE_VARIANT))

    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.EMOJI_EVENTS if done else ft.Icons.FLAG_OUTLINED,
                                color=INCOME_COLOR if done else ft.Colors.BLUE),
                        ft.Text(g.name, weight=ft.FontWeight.W_600, expand=True, max_lines=1),
                        ft.PopupMenuButton(
                            items=[
                                ft.PopupMenuItem(content="Edit", icon=ft.Icons.EDIT,
                                                 on_click=lambda e: open_goal_dialog(app, g)),
                                ft.PopupMenuItem(content="Withdraw", icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                                 on_click=lambda e: open_contribution_dialog(app, g, withdraw=True)),
                                ft.PopupMenuItem(
                                    content="Delete", icon=ft.Icons.DELETE_OUTLINE,
                                    on_click=lambda e: confirm_dialog(
                                        app, "Delete goal?", f"Delete '{g.name}'? This can't be undone.",
                                        lambda: (app.db.delete_goal(g.id), app.refresh()), # pyright: ignore[reportArgumentType]
                                    ),
                                ),
                            ]
                        ),
                    ],
                ),
                ft.Text(f"{money(g.saved, cur)} of {money(g.target, cur)}", size=13),
                ft.ProgressBar(value=min(ratio, 1), color=INCOME_COLOR if done else ft.Colors.BLUE, bar_height=10,
                               border_radius=5, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST),
                ft.Row([ft.Text(f"{min(ratio, 1) * 100:.0f}%", size=12, weight=ft.FontWeight.BOLD), *details],
                       spacing=10, wrap=True),
                ft.FilledTonalButton("Add money", icon=ft.Icons.ADD, disabled=done,
                                     on_click=lambda e: open_contribution_dialog(app, g)),
            ],
            spacing=10,
        ),
        col={"xs": 12, "sm": 6, "lg": 4},
    )


def open_goal_dialog(app: "ExpenseApp", goal: SavingsGoal | None = None) -> None:
    page = app.page
    state = {"deadline": goal.deadline if goal else None}
    name = ft.TextField(label="Goal name", value=goal.name if goal else "", autofocus=True, max_length=40)
    target = ft.TextField(label="Target amount", prefix=ft.Text(f"{app.currency} "),
                          value=f"{goal.target:.2f}" if goal else "", keyboard_type=ft.KeyboardType.NUMBER)
    deadline_text = ft.Text()

    def show_deadline():
        deadline_text.value = (date.fromisoformat(state["deadline"]).strftime("%d %b %Y")
                               if state["deadline"] else "No deadline")

    def picked(e):
        if e.control.value:
            v = e.control.value
            state["deadline"] = (v.date() if hasattr(v, "date") else v).isoformat()
            show_deadline()
            page.update()

    def clear_deadline(e):
        state["deadline"] = None
        show_deadline()
        page.update()

    show_deadline()

    def save(e):
        amount = parse_amount(target.value)
        name.error = None if name.value.strip() else "Give your goal a name"
        target.error = None if amount else "Enter a target greater than 0"
        if name.error or target.error:
            page.update()
            return
        if goal:
            app.db.update_goal(goal.id, name.value, amount, state["deadline"]) # pyright: ignore[reportArgumentType]
        else:
            app.db.add_goal(name.value, amount, state["deadline"]) # pyright: ignore[reportArgumentType]
        page.pop_dialog()
        app.toast("Goal saved")
        app.refresh()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Edit goal" if goal else "New savings goal"),
            content=ft.Container(
                ft.Column(
                    [
                        name,
                        target,
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.EVENT, size=20),
                                deadline_text,
                                ft.TextButton("Pick", on_click=lambda e: page.show_dialog(
                                    ft.DatePicker(first_date=date.today(),
                                                  last_date=date(date.today().year + 10, 12, 31),
                                                  on_change=picked))),
                                ft.TextButton("Clear", on_click=clear_deadline),
                            ],
                            wrap=True,
                        ),
                    ],
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=380,
            ),
            actions=[ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Save", on_click=save)],
        )
    )


def open_contribution_dialog(app: "ExpenseApp", goal: SavingsGoal, withdraw: bool = False) -> None:
    page = app.page
    amount_field = ft.TextField(label="Amount", prefix=ft.Text(f"{app.currency} "), autofocus=True,
                                keyboard_type=ft.KeyboardType.NUMBER)

    def save(e):
        amount = parse_amount(amount_field.value)
        if amount is None:
            amount_field.error = "Enter an amount greater than 0"
            page.update()
            return
        if withdraw and amount > goal.saved:
            amount_field.error = f"You only have {money(goal.saved, app.currency)} saved"
            page.update()
            return
        app.db.contribute_to_goal(goal.id, -amount if withdraw else amount)
        page.pop_dialog()
        app.toast(f"{'Withdrew' if withdraw else 'Added'} {money(amount, app.currency)}")
        app.refresh()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(f"{'Withdraw from' if withdraw else 'Add to'} {goal.name}"),
            content=ft.Container(amount_field, width=320),
            actions=[ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                     ft.FilledButton("Withdraw" if withdraw else "Add", on_click=save)],
        )
    )
