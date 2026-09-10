# Printer Hisob — Deploy qo'llanmasi (Ubuntu/Debian)

Arxitektura: **nginx** (frontend statik + `/api` proxy) → **uvicorn** (systemd) → **PostgreSQL**.
Frontend va API bir xil origin'da bo'lgani uchun CORS kerak emas.

Quyida `user` foydalanuvchi va `/home/user/print-hisob` yo'li deb faraz qilinadi — o'zingiznikiga moslang.

---

## 0. Kerakli paketlar
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql nginx curl
# Node.js 20 (frontend build uchun)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## 1. PostgreSQL
```bash
sudo -u postgres psql <<'SQL'
CREATE USER print_hisob WITH PASSWORD 'KUCHLI_DB_PAROL';
CREATE DATABASE print_hisob_db OWNER print_hisob;
SQL
```
> Yangi bo'sh baza — jadvallar backend birinchi ishga tushganda `AUTO_CREATE_TABLES=true`
> orqali avtomatik yaratiladi (duplex, document_pages, position bilan). Qo'lda ALTER shart emas.

## 2. Backend (FastAPI + venv + systemd)
```bash
cd /home/user/print-hisob/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# .env yarating (namunadan) va real qiymatlar bilan to'ldiring:
cp .env.production.example .env
nano .env          # DATABASE_URL, API_KEY, AUTH_PASSWORD, JWT_SECRET ni to'ldiring
# Maxfiy kalit generatsiya:  openssl rand -hex 32

# Qo'lda sinab ko'ring (ixtiyoriy):
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
#   -> curl http://127.0.0.1:8000/health  => {"status":"ok","database":"ok"}
#   (Ctrl+C bilan to'xtating)
```
systemd xizmati:
```bash
sudo cp /home/user/print-hisob/deploy/printer-hisob-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now printer-hisob-api
sudo systemctl status printer-hisob-api      # active (running) bo'lishi kerak
journalctl -u printer-hisob-api -f           # loglar
```

## 3. Frontend (Vue build)
```bash
cd /home/user/print-hisob/dashboard
cp .env.production.example .env               # VITE_API_BASE= (bo'sh) qoladi
npm ci
npm run build                                 # -> dashboard/dist/
```

## 4. Nginx
```bash
sudo cp /home/user/print-hisob/deploy/nginx.conf /etc/nginx/sites-available/printer-hisob
# server_name va root yo'lini tekshiring/tahrirlang:
sudo nano /etc/nginx/sites-available/printer-hisob
sudo ln -s /etc/nginx/sites-available/printer-hisob /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # standart sahifani o'chiring
sudo nginx -t && sudo systemctl reload nginx
```
Tekshirish: brauzerda `http://SERVER_IP/` → login sahifasi. `http://SERVER_IP/health` → ok.

## 5. HTTPS (tavsiya etiladi — real domen bo'lsa)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d hisob.example.uz
```

## 6. .exe agentlarni sozlash
- POST manzili: `http://SERVER_IP/api/print-jobs` (yoki HTTPS domen).
- Sarlavha: `X-API-Key: <.env dagi API_KEY>`.

---

## Yangilanish (keyingi deploylar)
```bash
cd /home/user/print-hisob && git pull
# backend
cd api && .venv/bin/pip install -r requirements.txt && sudo systemctl restart printer-hisob-api
# frontend
cd ../dashboard && npm ci && npm run build      # nginx statikni darrov oladi
```

## Kvota endpointini yoqish (`/api/print-quotas`)

Agent (`PrintMonitor.exe`) har necha daqiqada `POST /api/print-quotas` ga murojaat
qiladi. Endpoint bo'lmasa `404` oladi va **mahalliy** (`appsettings.json` dagi)
limitni qo'llaydi — dashboarddagi kvota o'zgarishi unga yetib bormaydi.

Shu endpoint qo'shilgan versiyani chiqarayotganda:

**1. Prod `.env` ni yangilang.** Sozlama fayli namunadan nusxa olingani uchun eski
qiymat yozilgan bo'lishi mumkin — kod standartining o'zgarishi unga ta'sir qilmaydi:

```bash
cd /home/user/print-hisob/api
nano .env
```
```ini
DEFAULT_QUOTA_QUARTER=1000        # eski qiymat 300 edi
AGENT_QUOTA_PERIOD_TYPE=quarter   # agentga choraklik davr yuboriladi
AGENT_QUOTA_REPORT_USED=true      # haqiqiy sarf yuboriladi
```

**2. Jadval avtomatik yaratiladi.** `AUTO_CREATE_TABLES=true` bo'lgani uchun
`agent_quota_state` xizmat ishga tushganda o'zi paydo bo'ladi — qo'lda `ALTER`
kerak emas.

**3. Tekshiring:**
```bash
sudo systemctl restart printer-hisob-api
curl -s -X POST http://127.0.0.1:8000/api/print-quotas \
  -H "Content-Type: application/json" -H "X-API-Key: <API_KEY>" \
  -d '{"computer":"TEST","timestamp":"2026-01-01T00:00:00Z","users":[]}'
# -> {"periodKey":"2026-Q1","defaultLimit":1000,"users":[]}
```

> **Diqqat:** javobdagi `periodKey` agentga birinchi marta yetib borganda
> undagi hisoblagichlar **nolga tushadi** — limitdan oshib bloklangan xodimlar
> shu zahoti ochiladi. Keyin esa server bergan haqiqiy sarf (`used`) qo'llanadi,
> ya'ni chorakda 1000 varaqdan oshganlar yana bloklanadi. Kimlar ekanini
> oldindan ko'rish uchun: `scripts/Check-Prod.ps1`.

## Xatoliklarni tekshirish
- Backend: `journalctl -u printer-hisob-api -e`
- Nginx: `sudo tail -f /var/log/nginx/error.log`
- 502 Bad Gateway → backend ishlamayapti (`systemctl status printer-hisob-api`).
- Login "Serverni tekshiring" → `/api` proxy yoki backend ishlamayapti.
