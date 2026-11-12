# Printer Hisob: ichki portal uchun API

Ichki xizmatlar portalida har bir xodim o'z kabinetida printerdan foydalanishi haqidagi
ma'lumotni ko'radi:

- davr uchun normasi va qancha ishlatgani;
- qaysi printerlardan chop eta olishi;
- qaysi printerlardan chop etgani va so'nggi ishlari.

Bu hujjat portal dasturchilari uchun.

## Ulanish

| | |
| --- | --- |
| Manzil | `https://print.madaniyhayot.uz/api/portal/v1` |
| Kalit | `X-Portal-Key: <kalit>` sarlavhasi |
| Format | JSON, UTF-8. Vaqtlar ISO-8601, UTC |
| Swagger | `https://print.madaniyhayot.uz/openapi.json`, `portal` bo'limi |

Kalitni Printer Hisob administratori beradi.

### Xavfsizlik qoidalari

1. **So'rovni faqat portal serveri yuboradi, brauzer yubormaydi.** Kalit brauzerga
   chiqsa, istalgan xodim boshqalarning ma'lumotini o'qiy oladi. Shu sababli bu API'ga
   CORS ochilmagan.
2. **Faqat tizimga kirgan xodimning loginini yuboring.** API kim so'rayotganini
   tekshirmaydi, faqat kalitni tekshiradi. Loginni portal sessiyasidan oling. URL yoki
   formadan kelgan loginni ishlatmang.
3. Hujjat nomlari shaxsiy ma'lumot hisoblanadi. Ularni faqat xodimning o'ziga ko'rsating.

Login har qanday yozilishda qabul qilinadi: `a.karimov`, `A.Karimov`, `MADANIYAT\a.karimov`.

## 1. Kabinet ma'lumoti

```
GET /api/portal/v1/employees/{login}/printing
```

Kabinetdagi "Printer" bo'limi uchun bitta so'rov yetadi.

| Parametr | Majburiy | Ma'nosi |
| --- | --- | --- |
| `period_type` | yo'q | `quarter` (chorak) yoki `month` (oy). Standart: `quarter` |
| `year` | yo'q | Yil. `period_no` bilan birga beriladi |
| `period_no` | yo'q | Chorak uchun 1–4, oy uchun 1–12 |

Davr berilmasa joriy chorak olinadi. Kabinet odatda shuni ko'rsatadi. O'tgan davr bilan
solishtirish uchun shu so'rovni o'tgan davr uchun ham yuboring.

### Javob namunasi

```json
{
  "employee": {
    "login": "a.karimov",
    "fullName": "Karimov Aziz",
    "department": "Raqamlashtirish bo'limi",
    "position": "Bosh mutaxassis",
    "status": "active"
  },
  "period": {
    "periodType": "quarter",
    "year": 2026,
    "periodNo": 4,
    "label": "2026-yil, 4-chorak",
    "start": "2026-10-01T00:00:00Z",
    "end": "2027-01-01T00:00:00Z"
  },
  "quota": {
    "allocated": 1000,
    "used": 356,
    "usedFromLinked": 0,
    "usedTotal": 356,
    "remaining": 644,
    "percent": 35.6,
    "overLimit": false,
    "isDefault": true,
    "linkedLogins": [],
    "chargedTo": null
  },
  "access": {
    "canPrint": true,
    "mode": "common",
    "groupName": null,
    "printers": [
      { "name": "3-qavat, Canon rangli", "ip": "192.168.30.120", "common": true }
    ]
  },
  "printers": [
    {
      "name": "3-qavat, Canon rangli",
      "ip": "192.168.30.120",
      "pages": 308,
      "jobs": 104,
      "failedJobs": 0,
      "lastPrintedAt": "2026-11-10T10:30:00Z",
      "allowed": true
    },
    {
      "name": "Canon MF3010",
      "ip": null,
      "pages": 48,
      "jobs": 32,
      "failedJobs": 0,
      "lastPrintedAt": "2026-10-30T07:01:00Z",
      "allowed": false
    }
  ],
  "daily": [
    { "date": "2026-11-10", "pages": 14, "jobs": 5 }
  ],
  "generatedAt": "2026-11-12T13:26:53Z"
}
```

### `employee`

| Maydon | Ma'nosi |
| --- | --- |
| `status` | `active`: AD'da ishlaydi. `inactive`: AD'dan chiqarilgan. `unknown`: AD'da yo'q, faqat chop etish tarixi bor |

### `quota`: norma

**Norma chop etishni to'xtatmaydi.** U faqat ko'rsatkich: xodim normadan oshsa ham chop
etaveradi. Chop eta olish yoki olmaslik `access.canPrint` da ko'rinadi.

| Maydon | Ma'nosi |
| --- | --- |
| `allocated` | Davr uchun norma, varaq |
| `used` | Xodimning o'zi chop etgan varaqlar |
| `usedFromLinked` | Unga biriktirilgan loginlardan qo'shilgan varaqlar, masalan amaliyotchi |
| `usedTotal` | `used + usedFromLinked`. Norma shu son bilan solishtiriladi |
| `remaining` | `allocated - usedTotal`. Normadan oshsa manfiy bo'ladi |
| `percent` | `usedTotal / allocated * 100`. Norma 0 bo'lsa `null` |
| `overLimit` | Normadan oshganmi |
| `isDefault` | `true`: xodimga alohida norma belgilanmagan, standart norma olingan |
| `linkedLogins` | Varaqlari shu xodim hisobiga qo'shiladigan loginlar |
| `chargedTo` | Bu xodim boshqa xodimga biriktirilgan bo'lsa, o'sha xodimning logini |

Hisobga kirmaydigan ishlar:

- Microsoft Print to PDF kabi virtual printerlar, chunki ular qog'oz sarflamaydi;
- bekor qilingan ishlar.

Raqamlar Printer Hisob dashboard'idagi bilan bir xil.

### `access`: printer ruxsati

| `mode` | Ma'nosi | Kabinetda yozish mumkin bo'lgan matn |
| --- | --- | --- |
| `common` | Faqat umumiy printerlar | "Siz quyidagi umumiy printerlardan chop eta olasiz" |
| `common_and_group` | Umumiy printerlar va guruhiga berilgan printerlar | "Umumiy printerlar va guruhingiz printerlari" |
| `all` | Barcha printerlar | "Barcha printerlardan chop eta olasiz" |
| `blocked` | Chop etish to'xtatilgan, `canPrint: false` | "Chop etish to'xtatilgan. AKT bo'limiga murojaat qiling" |

`printers` ro'yxati `common` va `common_and_group` rejimlarida to'ladi. Boshqa
rejimlarda u bo'sh keladi. Har bir printerda:

- `name`: printer nomi;
- `ip`: IP manzil, USB printerda `null`;
- `common`: umumiy printer bo'lsa `true`.

`groupName`: xodim istisno guruhida bo'lsa, guruh nomi.

### `printers`: davrda ishlatilgan printerlar

Ro'yxat varaqlar soni bo'yicha kamayish tartibida. Har bir printerda:

- `pages`, `jobs`, `failedJobs`: varaqlar, ishlar va xatolar soni;
- `lastPrintedAt`: shu printerdan oxirgi chop etish vaqti;
- `allowed`: hozir shu printerdan chop etishga ruxsat bormi.

`allowed: false` holati odatda shunday paydo bo'ladi: xodim cheklov kiritilishidan oldin
shu printerdan chop etgan, endi esa bu printer unga yopiq.

### `daily`: kunlik sarf

`daily` ro'yxatida faqat chop etilgan kunlar bor. Bo'sh kunlarni grafik uchun o'zingiz
0 bilan to'ldiring. Kun chegarasi UTC bo'yicha, ya'ni Toshkent vaqti bilan 05:00.

## 2. Chop etishlar ro'yxati

```
GET /api/portal/v1/employees/{login}/jobs
```

Xodimning o'z ishlari, eng yangisidan boshlab. "Barchasi" sahifasi uchun.

| Parametr | Ma'nosi |
| --- | --- |
| `limit` | 1–100, standart 20 |
| `offset` | Sahifalash uchun, standart 0 |
| `since` | Shu vaqtdan boshlab, ISO-8601. Ixtiyoriy |
| `until` | Shu vaqtgacha, chegaraning o'zi kirmaydi. Ixtiyoriy |

Jami soni `X-Total-Count` javob sarlavhasida keladi.

```json
[
  {
    "printedAt": "2026-11-10T10:30:00Z",
    "document": "Buyruq loyihasi.docx",
    "printer": "3-qavat, Canon rangli",
    "printerIp": "192.168.30.120",
    "computer": "RQ-PC-07",
    "pages": 4,
    "success": true,
    "reason": null,
    "counted": true
  }
]
```

| Maydon | Ma'nosi |
| --- | --- |
| `counted` | Normaga kiradimi. PDF va bekor qilingan ishlar ham ro'yxatda ko'rinadi, lekin ularda `false` |
| `success`, `reason` | Ish bajarilmagan bo'lsa, `reason` da sababi |

## Xatolar

| Kod | Qachon |
| --- | --- |
| 401 | `X-Portal-Key` yo'q yoki noto'g'ri |
| 404 | Login AD'da ham, chop etish tarixida ham yo'q |
| 422 | Davr parametri noto'g'ri, masalan `year` bor-u `period_no` yo'q |
| 503 | Serverda portal kaliti hali o'rnatilmagan |

Xato javobida `detail` maydoni bo'ladi, unda o'zbekcha izoh.

## Misol

```bash
curl -H "X-Portal-Key: $PORTAL_KEY" \
  "https://print.madaniyhayot.uz/api/portal/v1/employees/a.karimov/printing"
```

Portal serverida, masalan Node.js'da:

```js
async function printerInfo(login) {
  const url = `https://print.madaniyhayot.uz/api/portal/v1/employees/${encodeURIComponent(login)}/printing`
  const res = await fetch(url, { headers: { 'X-Portal-Key': process.env.PRINT_PORTAL_KEY } })
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Printer Hisob: ${res.status}`)
  return res.json()
}
```

Ma'lumot real vaqtda emas. Agentlar chop etishlarni bir necha daqiqa ichida yuboradi,
xodimlar ro'yxati esa AD'dan soatiga bir marta yangilanadi. Shuning uchun javobni portalda
1–5 daqiqa keshlash mumkin.

## Versiya

URL'dagi `v1` o'zgarmaydi. Mavjud maydonlar o'chirilmaydi va ma'nosi o'zgarmaydi, yangi
maydonlar qo'shilishi mumkin. Shuning uchun notanish maydonlarga e'tibor bermang.
