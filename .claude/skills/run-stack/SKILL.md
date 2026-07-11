---
name: run-stack
description: Run the full Printer Hisob stack locally — PostgreSQL (docker), FastAPI backend (uvicorn), and the Vue dashboard (vite). Use when verifying a change end-to-end or when asked to "start / run the app / see the API or dashboard".
---

# Run the Printer Hisob stack

Three parts: **DB → API → Dashboard**. Start each in its own terminal (or in the background).

## 1. PostgreSQL (Docker)
```bash
cd "d:/python projects/print-hisob/api"
docker compose up -d db
docker compose ps          # wait until healthy
```
No Docker? Create a local `printer_hisob` database and adjust `DATABASE_URL` in `.env`.

## 2. Backend API (FastAPI)
```bash
cd "d:/python projects/print-hisob/api"
# venv already exists (.venv). Otherwise:
#   python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```
Check:
```bash
curl http://localhost:8000/health          # {"status":"ok","database":"ok"}
```
- Swagger UI: http://localhost:8000/docs
- If `.env` has `API_KEY`, add `-H "X-API-Key: <key>"` to requests.
- Tests: `.venv/Scripts/python -m pytest -q` (no DB required).

## 3. Dashboard (Vue + Vite)
```bash
cd "d:/python projects/print-hisob/dashboard"
npm install        # first time
npm run dev        # http://localhost:5173
```
Set `dashboard/.env` with `VITE_API_BASE=http://localhost:8000` and `VITE_API_KEY=...` if needed.

## End-to-end verify
1. DB is `healthy`, API `/health` returns `ok`.
2. Send sample data with the `seed-data` skill.
3. `curl "http://localhost:8000/api/print-jobs?limit=5"` returns rows.
4. The dashboard KPIs/charts reflect that data for the selected quarter.

If ports are busy: change the API `--port`, the Vite `--port`, and update the dashboard `.env`.
