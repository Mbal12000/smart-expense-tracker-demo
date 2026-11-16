# Smart Expense Tracker

A Flet (Python + Flutter) app that helps students and young professionals **track spending**, **set monthly budgets** and **monitor savings**. It runs on desktop, in the browser, and on mobile (Android/iOS), and keeps all data on the device in SQLite.

## Features

- **Dashboard**: income, spending, money left over and total saved for the month. It also shows a budget bar with a "safe to spend per day" figure, a category breakdown, a 6-month income vs spending trend, and recent transactions.
- **Smart insights**: warns when a category goes past 80% or 100% of its budget, names your biggest expense, compares spending with last month, and checks your savings rate against the 20% rule of thumb.
- **Transactions**: add, edit or delete income and expenses. You can search, filter by type, and see them grouped by day with daily totals.
- **Budgets**: set an *Overall* monthly limit plus per-category limits. Bars turn amber at 80% and red when you go over. "Copy last month" carries budgets forward, and spending without a budget is listed separately.
- **Savings goals**: set targets with optional deadlines and add or withdraw money. The app shows how much to save each month to hit the deadline.
- **Settings**: currency (R, $, €, £, ₦, KSh, ₹), dark mode, CSV export, sample data and full reset.
- Student-friendly categories: *Data & Airtime*, *Education*, *Bursary / Scholarship*, *Allowance*, *Side Hustle* and more.

## Project structure

```
smart_expense_tracker/
├── pyproject.toml          # project + `flet build` config
├── requirements.txt
├── README.md
├── src/
│   ├── main.py             # app shell: app bar, month switcher, navigation, FAB
│   ├── database.py         # SQLite layer (transactions, budgets, goals, settings)
│   ├── utils.py            # money formatting, month maths, category icons/colours
│   ├── components.py       # cards, tiles, transaction dialog, confirm dialog
│   └── views/
│       ├── __init__.py
│       ├── dashboard.py
│       ├── transactions.py
│       ├── budgets.py
│       ├── savings.py
│       └── settings.py
└── tests/
    └── test_app.py
```

## Getting started

```bash
cd smart_expense_tracker
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

flet run            # desktop window
flet run --web      # in the browser
```

On first launch, click **Load sample data** to explore the app with a realistic month of data. You can clear it later in Settings.

## Tests

```bash
python -m pytest tests -q
```

## Building for mobile / desktop

```bash
flet build apk       # Android
flet build ipa       # iOS (on macOS)
flet build windows   # or macos / linux / web
```

## Where data is stored

- Packaged app: Flet's app data folder (`FLET_APP_STORAGE_DATA`).
- `flet run`: `~/.smart_expense_tracker/expenses.db`.

CSV exports go to your `Downloads` folder when it exists, otherwise next to the database.

## Public portfolio demo

A Render deployment configuration is included in `render.yaml`. See `README-DEPLOY.md` for setup instructions and the public-demo privacy behaviour. The hosted demo creates a separate temporary SQLite database for each browser session and loads sample data automatically. Do not enter real financial information; demo data may reset when the service restarts or redeploys.
