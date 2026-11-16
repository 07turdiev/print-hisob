# Printer Hisob: ichki portal uchun API

Ichki xizmatlar portalida har bir xodim o'z kabinetida printerdan foydalanishi haqidagi
ma'lumotni ko'radi:

- davr uchun normasi va qancha ishlatgani, istalgan davr uchun;
- unga biriktirilgan loginlar va ularning sarfi;
- so'nggi davrlar tarixi;
- qaysi printerlardan chop eta olishi;
- qaysi printerlardan chop etgani va so'nggi ishlari.

Rahbariyat uchun bo'limlar kesimi ham bor.

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
3. **Bo'limlar kesimini faqat `Portal-Rahbariyat` guruhiga ko'rsating.** API bu huquqni
   tekshirmaydi, uni portal tekshiradi.
4. Hujjat nomlari shaxsiy ma'lumot hisoblanadi. Ular faqat `/employees/{login}/jobs` da
   qaytadi va faqat xodimning o'ziga ko'rsatiladi. Bo'lim endpoint'larida hujjat,
   kompyuter va printer ma'lumoti yo'q, faqat yig'ma raqamlar bor.

Login har qanday yozilishda qabul qilinadi: `a.karimov`, `A.Karimov`, `MADANIYAT\a.karimov`.

## Endpoint'lar

| Yo'l | Kim uchun | Nima beradi |
| --- | --- | --- |
| `GET /employees/{login}/printing` | xodimning o'zi | Norma, biriktirishlar, ruxsat, ishlatilgan printerlar, kunlik sarf |
| `GET /employees/{login}/history` | xodimning o'zi | So'nggi davrlar normasi va sarfi |
| `GET /employees/{login}/jobs` | xodimning o'zi | Chop etishlar ro'yxati, hujjat nomlari bilan |
| `GET /periods` | hamma | Davr tanlash ro'yxatining chegaralari |
| `GET /departments` | rahbariyat | Bo'limlar kesimi |
| `GET /departments/{department}/employees` | rahbariyat | Bo'lim xodimlarining normasi va sarfi |

Barcha yo'llar `https://print.madaniyhayot.uz/api/portal/v1` dan keyin yoziladi.

### Davr parametrlari

`/printing` va bo'lim endpoint'lari bir xil davr parametrlarini oladi:

| Parametr | Majburiy | Ma'nosi |
| --- | --- | --- |
| `period_type` | yo'q | `quarter` (chorak) yoki `month` (oy). Standart: `quarter` |
| `year` | yo'q | Yil. `period_no` bilan birga beriladi |
| `period_no` | yo'q | Chorak uchun 1–4, oy uchun 1–12 |

Davr berilmasa joriy davr olinadi. Davr tanlash ro'yxatini `/periods` javobi bo'yicha
quring.

Har bir javobdagi `period` obyekti:

| Maydon | Ma'nosi |
| --- | --- |
| `periodType`, `year`, `periodNo` | Davr |
| `label` | Ko'rsatish uchun nom: `2026-yil, 4-chorak` yoki `2026-yil, Noyabr` |
| `start`, `end` | Davr chegaralari. `start` kiradi, `end` kirmaydi |
| `isCurrent` | Hozirgi davrmi |

Davr chegaralari UTC bo'yicha. Toshkent vaqti bilan davrning birinchi kuni soat 05:00
gacha chop etilgan ish oldingi davrga tushadi.

## 1. Kabinet ma'lumoti

```
GET /api/portal/v1/employees/{login}/printing
```

Kabinetdagi "Printer" bo'limi uchun bitta so'rov yetadi. Parametrlar: yuqoridagi davr
parametrlari.

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
    "end": "2027-01-01T00:00:00Z",
    "isCurrent": true
  },
  "quota": {
    "allocated": 600,
    "used": 12,
    "usedFromLinked": 5,
    "usedTotal": 17,
    "remaining": 583,
    "percent": 2.8,
    "overLimit": false,
    "isDefault": false,
    "allocatedSource": "explicit",
    "linkedLogins": ["amaliyotchi1", "amaliyotchi2"],
    "linked": [
      { "login": "amaliyotchi1", "fullName": null, "status": "unknown", "pages": 5, "jobs": 1 },
      { "login": "amaliyotchi2", "fullName": null, "status": "unknown", "pages": 0, "jobs": 0 }
    ],
    "chargedTo": null,
    "chargedToEmployee": null
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
      "pages": 12,
      "jobs": 1,
      "failedJobs": 0,
      "lastPrintedAt": "2026-11-10T10:30:00Z",
      "allowed": true
    }
  ],
  "daily": [
    { "date": "2026-11-10", "pages": 12, "jobs": 1 }
  ],
  "generatedAt": "2026-11-16T09:12:40Z"
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
| `percent` | `usedTotal / allocated * 100`, bir xona aniqlikda. Norma 0 bo'lsa `null` |
| `overLimit` | Normadan oshganmi |
| `isDefault` | `true`: xodimga alohida norma belgilanmagan, standart norma olingan |
| `allocatedSource` | `explicit`: normani admin alohida belgilagan. `default`: standart norma. `isDefault` bilan bir xil ma'noda, ko'rsatish uchun qulayroq |
| `linkedLogins` | Varaqlari shu xodim hisobiga qo'shiladigan loginlar |
| `linked` | Shu loginlar batafsil: har biri uchun quyidagi jadval |
| `chargedTo` | Bu xodim boshqa xodimga biriktirilgan bo'lsa, o'sha xodimning logini |
| `chargedToEmployee` | O'sha xodim batafsil: `{ login, fullName, status }`. Biriktirilmagan bo'lsa `null` |

`linked` ro'yxatining har bir elementi:

| Maydon | Ma'nosi |
| --- | --- |
| `login` | Biriktirilgan login |
| `fullName` | F.I.Sh. AD'da yo'q bo'lsa `null` |
| `status` | `active`, `inactive` yoki `unknown`, `employee.status` bilan bir xil ma'noda |
| `pages` | Shu davrda hisobga kiradigan varaqlari |
| `jobs` | Shu davrda hisobga kiradigan ishlari |

Sarfi 0 bo'lgan loginlar ham ro'yxatda turadi. `linked` dagi `pages` yig'indisi
`usedFromLinked` ga teng.

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

## 2. Davrlar tarixi

```
GET /api/portal/v1/employees/{login}/history?period_type=quarter&count=4
```

Joriy davr va undan oldingi davrlar, eng yangisi birinchi.

| Parametr | Ma'nosi |
| --- | --- |
| `period_type` | `quarter` yoki `month`. Standart: `quarter` |
| `count` | Nechta davr, joriy davr bilan birga: 1–12. Standart: 4 |

```json
[
  {
    "period": {
      "periodType": "quarter", "year": 2026, "periodNo": 4, "label": "2026-yil, 4-chorak",
      "start": "2026-10-01T00:00:00Z", "end": "2027-01-01T00:00:00Z", "isCurrent": true
    },
    "allocated": 600,
    "used": 12,
    "usedFromLinked": 5,
    "usedTotal": 17,
    "remaining": 583,
    "percent": 2.8,
    "overLimit": false,
    "isDefault": false
  },
  {
    "period": {
      "periodType": "quarter", "year": 2026, "periodNo": 3, "label": "2026-yil, 3-chorak",
      "start": "2026-07-01T00:00:00Z", "end": "2026-10-01T00:00:00Z", "isCurrent": false
    },
    "allocated": 1000,
    "used": 40,
    "usedFromLinked": 0,
    "usedTotal": 40,
    "remaining": 960,
    "percent": 4.0,
    "overLimit": false,
    "isDefault": true
  }
]
```

Maydonlar ma'nosi `quota` dagi bilan bir xil. Har bir davrning raqamlari shu davr uchun
`/printing` qaytaradigan `quota` raqamlari bilan aynan bir xil.

> **Ogohlantirish: biriktirish hozirgi holat bo'yicha barcha davrlarga qo'llanadi.**
> Biriktirishlar tarixi saqlanmaydi. Masalan, amaliyotchi bugun xodimga biriktirilsa, uning
> o'tgan choraklardagi varaqlari ham shu xodimning o'sha choraklardagi `usedFromLinked`
> qiymatiga qo'shiladi. Biriktirish bekor qilinsa, aksincha, o'tgan davrlardan ham olib
> tashlanadi. Shuning uchun o'tgan davr raqami keyinroq o'zgarishi mumkin. Tarix ostida
> foydalanuvchiga shunday izoh ko'rsating: "Biriktirilgan xodimlar sarfi hozirgi
> biriktirishlar bo'yicha hisoblangan."

## 3. Mavjud davrlar

```
GET /api/portal/v1/periods
```

Davr tanlash ro'yxatining chegaralari uchun. Parametr yo'q.

```json
{
  "defaultPeriodType": "quarter",
  "current": {
    "quarter": { "periodType": "quarter", "year": 2026, "periodNo": 4, "label": "2026-yil, 4-chorak", "start": "2026-10-01T00:00:00Z", "end": "2027-01-01T00:00:00Z", "isCurrent": true },
    "month": { "periodType": "month", "year": 2026, "periodNo": 11, "label": "2026-yil, Noyabr", "start": "2026-11-01T00:00:00Z", "end": "2026-12-01T00:00:00Z", "isCurrent": true }
  },
  "earliest": {
    "quarter": { "periodType": "quarter", "year": 2026, "periodNo": 3, "label": "2026-yil, 3-chorak", "start": "2026-07-01T00:00:00Z", "end": "2026-10-01T00:00:00Z", "isCurrent": false },
    "month": { "periodType": "month", "year": 2026, "periodNo": 7, "label": "2026-yil, Iyul", "start": "2026-07-01T00:00:00Z", "end": "2026-08-01T00:00:00Z", "isCurrent": false }
  }
}
```

| Maydon | Ma'nosi |
| --- | --- |
| `defaultPeriodType` | Davr berilmaganda olinadigan tur |
| `current` | Joriy chorak va joriy oy |
| `earliest` | Hisobga kiradigan birinchi ish bo'lgan chorak va oy. Hali hech narsa chop etilmagan bo'lsa `null` |

Ro'yxatni `earliest` dan `current` gacha quring. Bu chegaralar butun tizim bo'yicha.
Xodim bu davrlarning ba'zilarida chop etmagan bo'lishi mumkin, unda uning raqamlari 0
bo'ladi.

## 4. Chop etishlar ro'yxati

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

## 5. Rahbariyat: bo'limlar kesimi

Bu ikki endpoint'ni faqat `Portal-Rahbariyat` guruhidagi foydalanuvchilarga ko'rsating.
Ularda hujjat, kompyuter va printer ma'lumoti yo'q.

Bo'lim AD'dagi joriy bo'lim bo'yicha olinadi. Xodim bo'limini almashtirsa, uning o'tgan
davrlardagi sarfi ham yangi bo'limida ko'rinadi.

### Bo'limlar ro'yxati

```
GET /api/portal/v1/departments?period_type=quarter&year=2026&period_no=4
```

Parametrlar: davr parametrlari.

```json
{
  "period": { "periodType": "quarter", "year": 2026, "periodNo": 4, "label": "2026-yil, 4-chorak", "start": "2026-10-01T00:00:00Z", "end": "2027-01-01T00:00:00Z", "isCurrent": true },
  "departments": [
    {
      "department": "Raqamlashtirish bo'limi",
      "name": "Raqamlashtirish bo'limi",
      "employeeCount": 2,
      "allocated": 1600,
      "used": 42,
      "jobs": 2,
      "percent": 2.6,
      "overLimitCount": 0
    },
    {
      "department": "Xalqaro aloqalar bo'limi",
      "name": "Xalqaro aloqalar bo'limi",
      "employeeCount": 1,
      "allocated": 1000,
      "used": 8,
      "jobs": 1,
      "percent": 0.8,
      "overLimitCount": 0
    },
    {
      "department": null,
      "name": "Bo'limi aniqlanmagan",
      "employeeCount": null,
      "allocated": null,
      "used": 8,
      "jobs": 2,
      "percent": null,
      "overLimitCount": null
    }
  ],
  "totalUsed": 58,
  "totalJobs": 5
}
```

| Maydon | Ma'nosi |
| --- | --- |
| `department` | Bo'lim nomi. Xodimlar ro'yxatini so'rashda shu qiymatni ishlating |
| `name` | Ko'rsatish uchun nom |
| `employeeCount` | **Faqat faol xodimlar soni.** AD'dan chiqarilgan xodimlar sanalmaydi |
| `allocated` | Faol xodimlar normalarining yig'indisi |
| `used` | Bo'limning haqiqiy qog'oz sarfi |
| `jobs` | Hisobga kiradigan ishlar soni |
| `percent` | `used / allocated * 100`, bir xona aniqlikda |
| `overLimitCount` | Normadan oshgan xodimlar soni |
| `totalUsed`, `totalJobs` | Barcha qatorlar yig'indisi, ya'ni davrning umumiy sarfi |

`used` qanday hisoblanadi:

- Har bir ish chop etgan xodimning bo'limida bir marta sanaladi. Biriktirilgan
  xodimning varag'i egasining bo'limiga qo'shilmaydi, shuning uchun hech narsa ikki marta
  sanalmaydi.
- AD'dan chiqarilgan xodimning shu davrdagi varaqlari uning oxirgi bo'limida sanaladi,
  garchi u `employeeCount` ga kirmasa ham.
- `overLimitCount` esa xodim darajasida hisoblanadi: xodimning `usedTotal` qiymati
  (o'zi va biriktirilganlar) normasidan oshsa, u sanaladi.

**Oxirgi qator, `"department": null`, "Bo'limi aniqlanmagan".** Unda AD'da yo'q loginlar
(masalan skaner yoki amaliyotchi hisoblari) va bo'limi ko'rsatilmagan xodimlarning sarfi
turadi. Unda faqat `used` va `jobs` bor, qolgan maydonlar `null`, xodimlar ro'yxati yo'q.
Bu qator har doim bor, sarf 0 bo'lsa ham. Shu qator bilan birga barcha qatorlar
yig'indisi Printer Hisob dashboard'idagi umumiy sarfga teng.

### Bo'lim xodimlari

```
GET /api/portal/v1/departments/{department}/employees?period_type=quarter&year=2026&period_no=4
```

`{department}` o'rniga `/departments` javobidagi `department` qiymatini URL uchun
kodlab qo'ying. Bo'lim nomida apostrof, bo'shliq yoki `/` bo'lishi mumkin:

```js
const url = `${BASE}/departments/${encodeURIComponent(department)}/employees`
// "Raqamlashtirish bo'limi" -> /departments/Raqamlashtirish%20bo'limi/employees
```

```json
{
  "period": { "periodType": "quarter", "year": 2026, "periodNo": 4, "label": "2026-yil, 4-chorak", "start": "2026-10-01T00:00:00Z", "end": "2027-01-01T00:00:00Z", "isCurrent": true },
  "department": "Raqamlashtirish bo'limi",
  "employees": [
    {
      "login": "d.rasulova",
      "fullName": "Rasulova Dilnoza",
      "status": "active",
      "allocated": 1000,
      "used": 30,
      "usedFromLinked": 0,
      "usedTotal": 30,
      "percent": 3.0,
      "overLimit": false,
      "blocked": false
    },
    {
      "login": "a.karimov",
      "fullName": "Karimov Aziz",
      "status": "active",
      "allocated": 600,
      "used": 12,
      "usedFromLinked": 5,
      "usedTotal": 17,
      "percent": 2.8,
      "overLimit": false,
      "blocked": false
    }
  ]
}
```

Ro'yxatda bo'limning barcha faol xodimlari bor, sarfi 0 bo'lsa ham. Shu davrda chop etgan
va keyin AD'dan chiqarilgan xodimlar ham `"status": "inactive"` bilan ko'rinadi. Ro'yxat
`usedTotal` bo'yicha kamayish tartibida.

Maydonlar ma'nosi `quota` dagi bilan bir xil. `blocked: true` xodim umuman chop eta
olmaydi. Xodimlar `used` qiymatlarining yig'indisi `/departments` dagi shu bo'lim `used`
qiymatiga teng.

## Xatolar

| Kod | Qachon |
| --- | --- |
| 401 | `X-Portal-Key` yo'q yoki noto'g'ri |
| 404 | Login AD'da ham, chop etish tarixida ham yo'q, yoki bunday bo'lim yo'q |
| 422 | Parametr noto'g'ri: `year` bor-u `period_no` yo'q, `period_no` oraliqdan tashqarida, `count` 1–12 dan tashqarida |
| 503 | Serverda portal kaliti hali o'rnatilmagan |

Xato javobida `detail` maydoni bo'ladi. 404 va 503 da u o'zbekcha izoh matni. 422 da
FastAPI'ning standart ro'yxati bo'lishi mumkin: unda qaysi parametr noto'g'ri ekani
ko'rsatiladi.

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
1–5 daqiqa keshlash mumkin. `/periods` kuniga bir marta yangilansa yetadi.

## Versiya

URL'dagi `v1` o'zgarmaydi. Mavjud maydonlar o'chirilmaydi va ma'nosi o'zgarmaydi, yangi
maydonlar qo'shilishi mumkin. Shuning uchun notanish maydonlarga e'tibor bermang.

| Sana | O'zgarish |
| --- | --- |
| 2026-11-12 | Birinchi versiya: `/printing`, `/jobs` |
| 2026-11-16 | `/printing` ga `quota.linked`, `quota.chargedToEmployee`, `quota.allocatedSource`, `period.isCurrent` qo'shildi. Yangi: `/history`, `/periods`, `/departments`, `/departments/{department}/employees` |
