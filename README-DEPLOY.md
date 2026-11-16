# Smart Expense Tracker — public demo deployment

This package is configured for a public interactive demo on Render.

## Important demo behaviour

- Every new browser session gets a separate SQLite database.
- The app starts with sample transactions, budgets and savings goals.
- Visitors can add, edit and delete demo data without sharing a database with other visitors.
- Data is temporary and may reset when the Render service restarts or redeploys. Do not enter real financial or personal information.
- This is a portfolio demonstration, not a production financial service.

## Deploy on Render

1. Create a new public GitHub repository, for example `smart-expense-tracker-demo`.
2. Extract this ZIP and upload the contents of this folder to the repository root. Keep `render.yaml`, `requirements.txt`, `src/`, and the image files at the root level.
3. Commit and push the files to the repository's `main` branch.
4. Sign in to Render and connect your GitHub account if prompted.
5. In Render, choose **New → Blueprint** and select the repository. Render will read `render.yaml` and create the web service.
6. Review the service settings and click **Apply**.
7. Wait for the build and deploy to finish. Open the `onrender.com` URL shown on the service page.
8. Test the app: add a sample transaction, switch tabs, set a budget, and create a savings goal.

The service uses the Render-provided `$PORT` through `FLET_SERVER_PORT` and starts Flet in headless web-server mode.

## Local run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
flet run --web --port 8000 src/main.py
```

## Portfolio link

After Render deploys successfully, add the resulting `https://<your-service>.onrender.com` URL to the Expense Tracker project card on your portfolio as the live demo link.
