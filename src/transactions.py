"""Transactions: searchable, filterable list for the selected month."""

from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

import flet as ft

from components import card, empty_state, open_transaction_dialog, signed_money, transaction_tile
from utils import EXPENSE_COLOR, INCOME_COLOR, money, month_label, pretty_date

if TYPE_CHECKING:
    from main import ExpenseApp


def build_transactions(app: "ExpenseApp") -> ft.Control:
    filters = app.view_state.setdefault("tx", {"kind": "all", "search": ""})
    list_col = ft.Column(spacing=0)
    summary = ft.Text(size=13, color=ft.Colors.ON_SURFACE_VARIANT)

    def render():
        kind = None if filters["kind"] == "all" else filters["kind"]
        txs = app.db.list_transactions(month=app.month, kind=kind, search=filters["search"].strip())
        list_col.controls.clear()
        if not txs:
            list_col.controls.append(
                empty_state(ft.Icons.RECEIPT_LONG, "No transactions found",
                            f"Nothing matches for {month_label(app.month)}.")
            )
        for day, items in groupby(txs, key=lambda t: t.date):
            items = list(items)
            net = sum(t.amount if t.kind == "income" else -t.amount for t in items)
            list_col.controls.append(
                ft.Container(
                    ft.Row(
                        [
                            ft.Text(pretty_date(day), size=12, weight=ft.FontWeight.W_600),
                            ft.Text(signed_money(net, app.currency), size=12,
                                    color=INCOME_COLOR if net >= 0 else EXPENSE_COLOR),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                )
            )
            list_col.controls += [transaction_tile(app, t, app.refresh, show_date=False) for t in items]
        income = sum(t.amount for t in txs if t.kind == "income")
        spent = sum(t.amount for t in txs if t.kind == "expense")
        summary.value = (f"{len(txs)} transaction(s) · In {money(income, app.currency)} · "
                         f"Out {money(spent, app.currency)}")

    def on_kind(e):
        filters["kind"] = e.control.selected[0]
        render()
        app.page.update()

    def on_search(e):
        filters["search"] = e.control.value or ""
        render()
        app.page.update()

    render()
    return ft.Column(
        [
            card(
                ft.Column(
                    [
                        ft.ResponsiveRow(
                            [
                                ft.TextField(
                                    hint_text="Search notes or categories",
                                    prefix_icon=ft.Icons.SEARCH,
                                    value=filters["search"],
                                    on_change=on_search,
                                    dense=True,
                                    col={"xs": 12, "md": 6},
                                ),
                                ft.Container(
                                    ft.SegmentedButton(
                                        segments=[
                                            ft.Segment(value="all", label="All"),
                                            ft.Segment(value="expense", label="Expenses"),
                                            ft.Segment(value="income", label="Income"),
                                        ],
                                        selected=[filters["kind"]],
                                        on_change=on_kind,
                                    ),
                                    col={"xs": 12, "md": 6},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            run_spacing=10,
                        ),
                        summary,
                    ],
                    spacing=10,
                )
            ),
            card(list_col, padding=4),
            ft.Row(
                [
                    ft.OutlinedButton("Add income", icon=ft.Icons.ARROW_DOWNWARD,
                                      on_click=lambda e: open_transaction_dialog(app, app.refresh,
                                                                                 default_kind="income")),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=12,
    )
