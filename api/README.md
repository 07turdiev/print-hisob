# Printer Hisob API

Ish stantsiyalaridagi agentlardan chop etish hodisalarini POST orqali qabul qilib,
PostgreSQL'ga yozadigan FastAPI xizmati.

## Ishga tushirish

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # Linux/macOS: cp .env.example .env
# .env ichida DATABASE_URL ni o'zingiznikiga moslang

docker compose up -d db           # yoki mavjud Postgres serveringizni ishlating
uvicorn app.main:app --reload
```

## Interaktiv hujjat

| Sahifa | Manzil |
|--------|--------|
| Swagger UI | <http://127.0.0.1:8000/docs> |
| ReDoc | <http://127.0.0.1:8000/redoc> |
| OpenAPI JSON | <http://127.0.0.1:8000/openapi.json> |

Swagger'da `POST /api/print-jobs` → **Try it out** bosilsa, tana namunasi tayyor holda
to'ldirilgan bo'ladi. `API_KEY` yoqilgan bo'lsa, yuqoridagi **Authorize** tugmasi orqali
kalitni kiriting — u `X-API-Key` sarlavhasiga qo'yiladi.

## Endpointlar

To'liq ro'yxat Swagger'da (`/docs`). Agent (`PrintMonitor.exe`) murojaat qiladigan
uchta endpoint — kontrakti `ENDPOINTS.uz.md` hujjatida belgilangan, **o'zgartirmang**:

| Metod | Yo'l | Auth | Vazifasi |
|-------|------|------|----------|
| `POST` | `/api/print-jobs` | `X-API-Key` | Bir kompyuterdan kelgan hodisalar paketini saqlaydi |
| `POST` | `/api/agent-status` | `X-API-Key` | Agentning sog'lik signali (heartbeat) |
| `POST` | `/api/print-quotas` | `X-API-Key` | Agent sarfni bildiradi, javobda limitlarni oladi |

Dashboard uchun (JWT `Authorization: Bearer`):

| Metod | Yo'l | Vazifasi |
|-------|------|----------|
| `GET` | `/api/print-jobs` | Yozuvlarni filtrlab qaytaradi |
| `GET` | `/api/stats/*` | Davr bo'yicha statistika (summary, employees, top, ...) |
| `GET`/`PUT` | `/api/quotas` | Xodim kvotalarini o'qish/belgilash |
| `GET` | `/health` | Xizmat va baza holati (auth talab qilinmaydi) |

### POST /api/print-quotas

Agent har necha daqiqada shu endpointga murojaat qiladi: so'rovda — shu mashinada
hisoblangan varaqlar, javobda — server bilgan haqiqiy sarf va qo'llanishi kerak
bo'lgan limitlar. Chop etish qarorini agent **mahalliy** qabul qiladi, shuning
uchun bu endpoint ishlamay qolsa ham chop etish to'xtamaydi — agent eski
keshlangan limitlar bilan davom etadi.

```bash
curl -X POST http://127.0.0.1:8000/api/print-quotas \
  -H "Content-Type: application/json" \
  -d '{"computer":"LAPTOP-JANE","timestamp":"2026-09-10T09:15:00Z",
       "users":[{"user":"jane","pagesUsedHere":42,"pagesUsed":137,"limit":1000}]}'
```

```json
{"periodKey":"2026-Q3","defaultLimit":1000,
 "users":[{"user":"jane","limit":1500,"used":945}]}
```

Uch nozik qoida (agent hujjatidan):

* `limit` **yuborilmasa yoki `null`** — "menda fikr yo'q", agent `defaultLimit`ga tushadi;
* `-1` — aniq cheklovsiz; `0` — so'zma-so'z: umuman chop eta olmaydi;
* **`periodKey` o'zgarishi agentdagi hisoblagichni nolga tushiradi** — format
  `app.periods.period_key` orqali barqaror hosil qilinadi (`2026-Q3`).

Foydalanuvchi nomlari registrga sezgir emas va `DOMAIN\` prefiksi olib tashlangan
holda solishtiriladi (`app.logins.normalize_login`): `MADANIYAT\E.Turdiyev`,
`e.turdiyev`, `E.TURDIYEV` — bitta odam.

Qaysi davr agentga yuborilishi `AGENT_QUOTA_PERIOD_TYPE` sozlamasida (standart
`quarter`), standart limit esa `DEFAULT_QUOTA_QUARTER` da (standart `1000`).

### POST /api/print-jobs

```bash
curl -X POST http://127.0.0.1:8000/api/print-jobs \
  -H "Content-Type: application/json" \
  --data-binary @payload.example.json
```

Javob:

```json
{ "computer": "DESKTOP-ABC123", "received": 2, "inserted": 2, "duplicates": 0 }
```

### GET /api/print-jobs

Filtrlar: `computer`, `user`, `printer`, `success`, `since`, `until`, `limit`, `offset`.

```bash
curl "http://127.0.0.1:8000/api/print-jobs?computer=DESKTOP-ABC123&success=false&limit=50"
```

## Ma'lumotlarni qayta ishlash qoidalari

- **Bo'sh satr → `NULL`.** `"printerIp": ""` va `"reason": ""` bazaga `NULL` bo'lib tushadi,
  shunda "qiymat yo'q" va "bo'sh matn" farqlanadi.
- **7 xonali kasr soniya.** .NET `DateTimeOffset.ToString("o")` `...10.1234567+00:00`
  ko'rinishida yuboradi. Postgres `timestamptz` 6 xonagacha (mikrosoniya) saqlaydi,
  ortiqcha raqam kesiladi.
- **Vaqt mintaqasi.** `timestamp` mintaqasiz kelsa UTC deb qabul qilinadi.
- **`printerIp` matn ustuni.** Agentlar ba'zan IP o'rniga port nomini (`WSD-...`, `USB001`)
  yuboradi, shuning uchun `INET` emas, `varchar`.
- **Dublikatlar.** Har bir hodisa uchun
  `sha256(computer|user|document|printer|timestamp)` dan `dedup_key` hisoblanadi va u
  unikal. Agent tarmoq uzilgach o'sha paketni qayta yuborsa, `ON CONFLICT DO NOTHING`
  tufayli takroriy qator qo'shilmaydi — javobda `inserted: 0, duplicates: N` ko'rinadi.
  Bir paket ichidagi takrorlar ham yig'ib tashlanadi.
- **Katta paketlar.** 500 qatordan iborat bo'laklarga bo'lib yoziladi (Postgres bitta
  so'rovda 65535 parametrni qabul qiladi). Paket eng ko'pi **60 000** hodisa
  (`MAX_JOBS_PER_BATCH`) — bu agentning buferidan (`MaxBufferedJobs`, standart
  50 000) ataylab katta. Aks holda uzoq uzilishdan keyin agent butun buferni bitta
  to'plamda yuboradi, server `422` qaytaradi, agent esa `2xx` olmagani uchun buferni
  tozalamaydi va o'sha to'plamni abadiy qayta yuboraveradi. nginx tomonida ham mos
  chegara kerak: `client_max_body_size 32m` (`deploy/nginx.conf`).

## Autentifikatsiya

`.env` da `API_KEY` to'ldirilsa, `/api/print-jobs` so'rovlari `X-API-Key` sarlavhasini
talab qiladi. Bo'sh qoldirilsa tekshiruv o'chadi (faqat ishonchli ichki tarmoq uchun).

```bash
curl -H "X-API-Key: ..." ...
```

## Testlar

```bash
pip install -r requirements-dev.txt
pytest
```

Testlar bazasiz ishlaydi — sessiya stub bilan almashtiriladi.

## Prod eslatmasi

`AUTO_CREATE_TABLES=true` ishga tushganda jadvalni yaratadi. Prod'da uni `false` qilib,
sxema o'zgarishlarini Alembic migratsiyalari orqali boshqaring.

## Jadval

```
print_jobs
  id          bigserial primary key
  computer    varchar(255)   not null
  user_name   varchar(255)   not null      -- JSON'dagi "user"
  document    text           not null
  printer     varchar(255)   not null
  printer_ip  varchar(255)   null          -- JSON'dagi "printerIp"
  pages       integer        not null
  printed_at  timestamptz    not null      -- JSON'dagi "timestamp"
  success     boolean        not null
  reason      text           null
  dedup_key   varchar(64)    not null unique
  created_at  timestamptz    not null default now()
```
