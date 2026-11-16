"""Reusable UI pieces: cards, avatars, empty states and the transaction form dialog."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Callable

import flet as ft

from database import EXPENSE_CATEGORIES, INCOME_CATEGORIES, Transaction
from utils import EXPENSE_COLOR, INCOME_COLOR, category_style, money, parse_amount, pretty_date

if TYPE_CHECKING:
    from main import ExpenseApp


def card(content: ft.Control, padding: int = 16, col=None, expand=None) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        border_radius=16,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        col=col if col is not None else 12,
        expand=expand,
    )


def section_title(text: str, action: ft.Control | None = None) -> ft.Row:
    return ft.Row(
        [ft.Text(text, size=16, weight=ft.FontWeight.W_600), action or ft.Container()],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def stat_card(label: str, value: str, icon: ft.IconData, color: str, col=None, hint: str = "") -> ft.Container:
    return card(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Container(
                            ft.Icon(icon, color=color, size=20),
                            bgcolor=ft.Colors.with_opacity(0.12, color),
                            border_radius=10,
                            padding=8,
                        ),
                        ft.Text(label, size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    spacing=10,
                ),
                ft.Text(value, size=22, weight=ft.FontWeight.BOLD),
                ft.Text(hint or " ", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            spacing=8,
        ),
        col=col or {"xs": 6, "md": 3},
    )


def category_avatar(category: str, size: int = 40) -> ft.Container:
    icon, color = category_style(category)
    return ft.Container(
        ft.Icon(icon, color=color, size=size * 0.5),
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=ft.Colors.with_opacity(0.14, color),
        alignment=ft.Alignment.CENTER,
    )


def empty_state(icon: ft.IconData, title: str, subtitle: str, action: ft.Control | None = None) -> ft.Container:
    controls = [
        ft.Icon(icon, size=56, color=ft.Colors.OUTLINE),
        ft.Text(title, size=16, weight=ft.FontWeight.W_600),
        ft.Text(subtitle, size=13, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
    ]
    if action:
        controls.append(action)
    return ft.Container(
        ft.Column(controls, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=32,
        alignment=ft.Alignment.CENTER,
    )


def signed_money(amount: float, symbol: str) -> str:
    return ("+ " if amount >= 0 else "- ") + money(abs(amount), symbol)


def transaction_tile(app: "ExpenseApp", tx: Transaction, on_changed: Callable[[], None],
                     show_date: bool = True) -> ft.ListTile:
    is_income = tx.kind == "income"
    amount_text = signed_money(tx.amount if is_income else -tx.amount, app.currency)
    return ft.ListTile(
        leading=category_avatar(tx.category), # pyright: ignore[reportCallIssue]
        title=ft.Text(tx.note or tx.category, weight=ft.FontWeight.W_500, max_lines=1),
        subtitle=ft.Text(f"{tx.category} · {pretty_date(tx.date)}" if show_date else tx.category, size=12),
        trailing=ft.Text(
            amount_text,
            color=INCOME_COLOR if is_income else EXPENSE_COLOR,
            weight=ft.FontWeight.W_600,
        ),
        on_click=lambda e: open_transaction_dialog(app, on_changed, tx),
    )


def _clear_error(control: ft.Control) -> None:
    if getattr(control, "error_text", None):
        control.error_text = None # pyright: ignore[reportAttributeAccessIssue]
        control.update()


def open_transaction_dialog(
    app: "ExpenseApp",
    on_saved: Callable[[], None],
    tx: Transaction | None = None,
    default_kind: str = "expense",
) -> None:
    """Add a new transaction, or edit/delete an existing one."""
    page = app.page
    state = {
        "kind": tx.kind if tx else default_kind,
        "date": date.fromisoformat(tx.date) if tx else date.today(),
    }

    def categories_for(kind: str) -> list[ft.DropdownOption]:
        cats = INCOME_CATEGORIES if kind == "income" else EXPENSE_CATEGORIES
        return [ft.DropdownOption(key=c, text=c) for c in cats]

    amount_field = ft.TextField(
        label="Amount",
        value=f"{tx.amount:.2f}" if tx else "",
        prefix=ft.Text(f"{app.currency} "),
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )
    category_dd = ft.Dropdown(
        label="Category",
        options=categories_for(state["kind"]),
        value=tx.category if tx else None,
        expand=True,
        on_select=lambda e: _clear_error(e.control),
    )
    note_field = ft.TextField(label="Note (optional)", value=tx.note if tx else "", max_length=80)
    date_text = ft.Text(state["date"].strftime("%d %b %Y"))

    def on_kind_change(e):
        state["kind"] = e.control.selected[0]
        category_dd.options = categories_for(state["kind"])
        category_dd.value = None
        page.update()

    kind_selector = ft.SegmentedButton(
        segments=[
            ft.Segment(value="expense", label="Expense", icon=ft.Icons.ARROW_UPWARD),
            ft.Segment(value="income", label="Income", icon=ft.Icons.ARROW_DOWNWARD),
        ],
        selected=[state["kind"]],
        on_change=on_kind_change,
    )

    def on_date_picked(e):
        if e.control.value:
            picked = e.control.value
            state["date"] = picked.date() if hasattr(picked, "date") else picked
            date_text.value = state["date"].strftime("%d %b %Y")
            page.update()

    def pick_date(e):
        page.show_dialog(
            ft.DatePicker(
                value=state["date"],
                first_date=date(2015, 1, 1),
                last_date=date(date.today().year + 1, 12, 31),
                on_change=on_date_picked,
            )
        )

    def save(e):
        amount = parse_amount(amount_field.value)
        ok = True
        amount_field.error = None
        category_dd.error_text = None
        if amount is None:
            amount_field.error = "Enter an amount greater than 0"
            ok = False
        if not category_dd.value:
            category_dd.error_text = "Choose a category"
            ok = False
        if not ok:
            page.update()
            return
        args = (state["kind"], amount, category_dd.value, note_field.value or "", state["date"].isoformat())
        if tx:
            app.db.update_transaction(tx.id, *args) # pyright: ignore[reportArgumentType]
        else:
            app.db.add_transaction(*args) # pyright: ignore[reportArgumentType]
        page.pop_dialog()
        app.toast("Transaction updated" if tx else "Transaction added")
        on_saved()

    def delete(e):
        assert tx is not None
        app.db.delete_transaction(tx.id)
        page.pop_dialog()
        app.toast("Transaction deleted")
        on_saved()

    actions: list[ft.Control] = []
    if tx:
        actions.append(ft.TextButton("Delete", icon=ft.Icons.DELETE_OUTLINE, on_click=delete,
                                     style=ft.ButtonStyle(color=EXPENSE_COLOR)))
    actions += [
        ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
        ft.FilledButton("Save", on_click=save),
    ]

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Edit transaction" if tx else "New transaction"),
            content=ft.Container(
                ft.Column(
                    [
                        kind_selector,
                        amount_field,
                        ft.Row([category_dd]),
                        note_field,
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.CALENDAR_MONTH, size=20),
                                date_text,
                                ft.TextButton("Change date", on_click=pick_date),
                            ]
                        ),
                    ],
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                width=400,
            ),
            actions=actions,
        )
    )


def confirm_dialog(app: "ExpenseApp", title: str, message: str, on_confirm: Callable[[], None],
                   confirm_text: str = "Delete") -> None:
    page = app.page

    def yes(e):
        page.pop_dialog()
        on_confirm()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton(confirm_text, on_click=yes,
                                style=ft.ButtonStyle(bgcolor=EXPENSE_COLOR, color=ft.Colors.WHITE)),
            ],
        )
    )
