---
name: seed-data
description: Seed the Printer Hisob API with sample data — print jobs, AD employees, and quotas — to populate the database for testing the dashboard, monthly/quarterly stats, quota views, and unmatched-user flagging. Use when asked for "test data / sample data / fill the dashboard".
---

# Seed sample data

The dashboard needs realistic data across three sources: **print jobs**, **AD employees**, and **quotas**. Seed all three so every panel (used-vs-quota, department rollups, unmatched users) has content. All ingest is idempotent, so re-sending is safe.

## 1. Print jobs — `POST /api/print-jobs`
We call the endpoint with batches. Because ingest is deduplicated, re-sending is safe (no duplicate rows) — this also mirrors the .exe agent's offline re-send behavior.

## Payload format (what the .exe agent sends)
See `api/payload.example.json`. Keys are **camelCase**, timestamp in .NET ISO ("o") format:
```json
{
  "computer": "DESKTOP-ABC123",
  "jobs": [
    {"user": "jsmith", "document": "Report.docx", "printer": "HP LaserJet M404",
     "printerIp": "192.168.1.50", "pages": 3,
     "timestamp": "2026-07-10T14:32:10.1234567+00:00", "success": true, "reason": ""}
  ]
}
```

## Quick way — send the existing sample
```bash
cd "d:/python projects/print-hisob/api"
curl -X POST http://localhost:8000/api/print-jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  --data @payload.example.json
```
Response: `{"received":N,"inserted":N,"duplicates":0}`.

## Generate richer data (so quarterly charts and quotas look real)
The dashboard reports by **quarter (Q1–Q4)** and per **employee quota**, so spread data across months and people. Write a small Python script into scratchpad:
- 4–6 computers, 8–12 employees, 3–5 printers.
- Spread `timestamp` across **the target quarter's months** (and optionally several quarters) so quarter selection has data.
- Generate `documentPages` (fayldagi sahifa, 1–40), set `duplex` true on ~40% of jobs, then `pages` (qog'oz/varaq soni) = `ceil(documentPages/2)` when duplex else `documentPages` — this mimics what the .exe sends (it does the duplex math). `pages` is the consumption metric; the backend sums it directly (no transformation). Make a few employees exceed a plausible quarterly quota so the over-limit highlight is visible; ~10% `success:false` with a non-empty `reason` (and `pages`/`documentPages` = 0).
- POST each batch to the endpoint above.

**Determinism:** the workflow/script sandbox forbids `datetime.now()` / `random.random()` with no seed. Pass the base date/period as an argument and use a **seeded** `random.Random(seed)` so runs are reproducible. Write the script as `scratchpad/seed.py` and run it with `.venv/Scripts/python scratchpad/seed.py`.

**Include unmatched users:** make 1–2 print `user` logins that do NOT exist in the AD employee set (step 2), so the dashboard's "unmatched / noma'lum foydalanuvchi" flag has something to show.

## 2. AD employees — `POST /api/ad-sync`
Mimic the hourly AD sync. Send a batch of employees so print `user` logins match:
- 8–12 employees with `login` (== print `user`), `full_name`, `department` (bo'lim), `position` (lavozim, e.g. "Bosh mutaxassis"), `active`. (There is no directorate/boshqarma field — org unit is just `department`.)
- Spread across 3–4 departments so department rollups and the grouped KPI CSV export are meaningful.
- Mark 1 employee `active:false` (departed) to test the "matched & inactive" badge.
- Leave the print-only logins from step 1 OUT of this set (they become "unmatched").

## 3. Quotas — `PUT /api/quotas`
Set limits for **both** granularities so both dashboard pages work:
- `period_type: "quarter"` — e.g. 1500 pages per employee for the target quarter.
- `period_type: "month"` — e.g. 500 pages per employee for the target month(s).
- Make a couple of employees exceed their limit (via step 1 page counts) so the over-limit highlight is visible.

## Reset
Clear all rows:
```bash
docker compose exec db psql -U postgres -d printer_hisob \
  -c "TRUNCATE print_jobs, employees, employee_quotas;"
```
(Adjust table names to what backend-dev created.)
