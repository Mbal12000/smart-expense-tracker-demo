"""Formatting helpers, month maths and category styling."""

from __future__ import annotations

from datetime import date, datetime

import flet as ft

CURRENCIES = {
    "R": "South African Rand (R)",
    "$": "US Dollar ($)",
    "€": "Euro (€)",
    "£": "British Pound (£)",
    "₦": "Nigerian Naira (₦)",
    "KSh": "Kenyan Shilling (KSh)",
    "₹": "Indian Rupee (₹)",
}

CATEGORY_STYLE: dict[str, tuple[ft.IconData, str]] = {
    "Food & Groceries": (ft.Icons.RESTAURANT, ft.Colors.ORANGE),
    "Transport": (ft.Icons.DIRECTIONS_BUS, ft.Colors.BLUE),
    "Rent & Housing": (ft.Icons.HOME, ft.Colors.BROWN),
    "Utilities": (ft.Icons.BOLT, ft.Colors.AMBER),
    "Data & Airtime": (ft.Icons.WIFI, ft.Colors.CYAN),
    "Education": (ft.Icons.SCHOOL, ft.Colors.INDIGO),
    "Entertainment": (ft.Icons.MOVIE, ft.Colors.PURPLE),
    "Shopping": (ft.Icons.SHOPPING_BAG, ft.Colors.PINK),
    "Health": (ft.Icons.LOCAL_HOSPITAL, ft.Colors.RED),
    "Personal Care": (ft.Icons.SPA, ft.Colors.TEAL),
    "Subscriptions": (ft.Icons.SUBSCRIPTIONS, ft.Colors.DEEP_PURPLE),
    "Gifts & Donations": (ft.Icons.CARD_GIFTCARD, ft.Colors.LIGHT_GREEN),
    "Other": (ft.Icons.CATEGORY, ft.Colors.BLUE_GREY),
    "Overall": (ft.Icons.ACCOUNT_BALANCE_WALLET, ft.Colors.GREEN),
    # income
    "Salary": (ft.Icons.WORK, ft.Colors.GREEN),
    "Allowance": (ft.Icons.FAMILY_RESTROOM, ft.Colors.GREEN),
    "Bursary / Scholarship": (ft.Icons.WORKSPACE_PREMIUM, ft.Colors.GREEN),
    "Side Hustle": (ft.Icons.STOREFRONT, ft.Colors.GREEN),
    "Freelance": (ft.Icons.LAPTOP_MAC, ft.Colors.GREEN),
    "Gift": (ft.Icons.REDEEM, ft.Colors.GREEN),
    "Other Income": (ft.Icons.ATTACH_MONEY, ft.Colors.GREEN),
}

INCOME_COLOR = ft.Colors.GREEN_600
EXPENSE_COLOR = ft.Colors.RED_400
WARNING_COLOR = ft.Colors.AMBER_700


def category_style(category: str) -> tuple[ft.IconData, str]:
    return CATEGORY_STYLE.get(category, (ft.Icons.CATEGORY, ft.Colors.BLUE_GREY))


def money(amount: float, symbol: str = "R") -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{symbol} {abs(amount):,.2f}".replace(",", " ")


def parse_amount(text: str | None) -> float | None:
    """Parse user input like '1 250,50' or '1,250.50'. Returns None if invalid/<=0."""
    if not text:
        return None
    cleaned = text.strip().replace(" ", "")
    if cleaned.count(",") == 1 and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        value = round(float(cleaned), 2)
    except ValueError:
        return None
    return value if value > 0 else None


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def shift_month(month: str, delta: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + delta
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def month_label(month: str, short: bool = False) -> str:
    dt = datetime.strptime(month + "-01", "%Y-%m-%d")
    return dt.strftime("%b %Y" if short else "%B %Y")


def pretty_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    today = date.today()
    if d == today:
        return "Today"
    if (today - d).days == 1:
        return "Yesterday"
    return d.strftime("%d %b %Y")


def progress_color(ratio: float) -> str:
    if ratio >= 1:
        return EXPENSE_COLOR
    if ratio >= 0.8:
        return WARNING_COLOR
    return INCOME_COLOR


def days_left_in_month(month: str) -> int:
    """Days remaining including today, or 0 if the month isn't the current one."""
    if month != current_month():
        return 0
    today = date.today()
    nxt = shift_month(month, 1)
    last = date.fromisoformat(nxt + "-01").toordinal() - 1
    return last - today.toordinal() + 1
