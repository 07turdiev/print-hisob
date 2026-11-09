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
> Jadvallar keyingi qadamda `alembic upgrade head` bilan yaratiladi.

## 2. Backend (FastAPI + venv + systemd)
```bash
cd /home/user/print-hisob/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# .env yarating (namunadan) va real qiymatlar bilan to'ldiring:
cp .env.production.example .env
nano .env          # DATABASE_URL, API_KEY, AUTH_PASSWORD, JWT_SECRET ni to'ldiring
# Maxfiy kalit generatsiya:  openssl rand -hex 32

.venv/bin/alembic upgrade head     # jadvallarni yaratadi

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

Kod GitHub'ga chiqqandan keyin serverda bitta buyruq:

```bash
cd /home/user/print-hisob && git fetch && bash deploy/deploy.sh
```

Skript shu tartibda ishlaydi: baza zaxirasi, kod, kutubxonalar, migratsiya, dashboard,
xizmatni qayta ishga tushirish, `/health` tekshiruvi. Biror qadam o'tmasa kod va dashboard
avvalgi holatiga qaytadi. Natijalar `~/print-hisob-backups/deploy.log` da yoziladi.

- Serverda fayllarni qo'lda o'zgartirmang. Commit qilinmagan o'zgarish bo'lsa skript
  ishlamaydi, faqat `dashboard/package-lock.json` istisno.
- Eski versiyaga qaytish: `bash deploy/deploy.sh --allow-older <commit>`.

## Baza sxemasi

Jadvallar `api/migrations/` dagi Alembic migratsiyalari bilan boshqariladi, prod'da
`AUTO_CREATE_TABLES=false`. Deploy skripti migratsiyani xizmat qayta ishga tushishidan
oldin bir marta bajaradi.

Migratsiya qo'shuvchi bo'lsin: skript orqaga qaytganda sxema joyida qoladi, shuning uchun
eski kod yangi sxemada ishlay olishi kerak. Ustun yoki jadvalni o'chirish alohida chiqariladi,
ularni ishlatadigan kod olib tashlangandan keyin.

## Zaxira

| Qachon | Kim oladi | Saqlanadi |
| --- | --- | --- |
| Har chiqarishdan oldin | `deploy.sh` | oxirgi 10 ta |
| Har kecha | cron | oxirgi 14 ta |

Cron yozuvi (`crontab -e`):

```
15 1 * * * bash /home/user/print-hisob/deploy/backup.sh daily >> /home/user/print-hisob-backups/backup.log 2>&1
```

Zaxiralar `~/print-hisob-backups/db/` da, ya'ni shu serverning o'zida. Disk ishdan chiqsa ular
ham yo'qoladi, shuning uchun nusxasini boshqa joyga ko'chirib turish kerak.

Tiklash (bazadagi joriy ma'lumot almashadi):

```bash
sudo systemctl stop printer-hisob-api
pg_restore --clean --if-exists --no-owner -h localhost -p 5434 -U print_hisob -d print_hisob_db FAYL.dump
sudo systemctl start printer-hisob-api
```

## Xatoliklarni tekshirish
- Backend: `journalctl -u printer-hisob-api -e`
- Nginx: `sudo tail -f /var/log/nginx/error.log`
- 502 Bad Gateway → backend ishlamayapti (`systemctl status printer-hisob-api`).
- Login "Serverni tekshiring" → `/api` proxy yoki backend ishlamayapti.
