# PrintMonitor agenti uchun topshiriq: printerlarni cheklash

Hujjat sanasi: 2026-11-09 · Madaniy Hayot · Asos: agent 1.6.1.0

## Nima uchun

Vazirlik topshirig'iga ko'ra xodimlar faqat umumiy foydalanish uchun belgilangan
printerlardan chop etishi kerak. Qolgan printerlarda chop etish texnik jihatdan cheklanadi,
ayrim xodimlarga vazir ruxsati bilan istisno beriladi.

Ruxsat ro'yxatini server beradi, to'sish qarorini esa **agent** qabul qiladi: ish navbatga
tushgan va printer qog'oz tortgan payt orasida serverga borib kelishga vaqt yo'q.

## Nima qilish kerak

| № | Ish | Majburiylik | Bo'lim |
| --- | --- | --- | --- |
| 1 | Server bergan `allowedPrinters` ro'yxatini qo'llash va diskda saqlash | majburiy | Ruxsatni tekshirish |
| 2 | To'silgan ishni serverga yuborish va foydalanuvchiga sababini aytish | majburiy | To'silgan ish |
| 3 | `printerMac` ni faqat ishonchli bo'lganda yuborish | majburiy | MAC manzil |
| 4 | Yangi versiya raqami (1.6.1.0 dan katta) | majburiy | Chiqarish tartibi |
| 5 | Ortiqcha "bekor qilingan" yozuvlar sababini aniqlash | tavsiya | Ortiqcha yozuvlar |

Endpointlar, autentifikatsiya va yuboriladigan maydonlar o'zgarmaydi. Yangi maydon qo'shish
shart emas.

**Avval javob bering:** 1.6.1.0 versiyasi `allowedPrinters` ni allaqachon qo'llayaptimi?
Serverdan buni ko'rib bo'lmaydi, chunki hozir hammaga `["*"]` ketyapti. Javobingiz ish
hajmini belgilaydi.

## Hozirgi holat

- Server javobida `allowedPrinters` 2026-yil 2-noyabrdan beri bor. Hozir hammaga `["*"]`
  ketmoqda, ya'ni hech kim cheklanmagan.
- Umumiy printerlar serverda belgilangan, lekin cheklov o'chiq. U agent tayyor bo'lgach
  yoqiladi.
- `limit: 0` bugun to'g'ri ishlayapti: oxirgi ikki kunda server `0` bergan 5 396 holatdan
  5 395 tasida agent ham `0` ni qo'llagan. To'sish mexanizmi tayyor, unga yangi sabab
  qo'shiladi.
- Flotda 155 ta agent bor, 138 tasi 1.6.1.0 versiyasida.

## Server bilan almashinuv

`POST /api/print-quotas`, sarlavha `X-Api-Key`. So'rov hozirgidek qoladi:

```json
{
  "computer": "LAPTOP-JANE",
  "periodKey": "2026-Q4",
  "timestamp": "2026-11-09T09:15:00Z",
  "users": [
    { "user": "MADANIYAT\\e.turdiyev", "pagesUsedHere": 42, "pagesUsed": 137, "limit": -1 }
  ]
}
```

Javob, cheklov yoqilgandan keyingi ko'rinishda:

```json
{
  "periodKey": "2026-Q4",
  "defaultLimit": -1,
  "allowedPrinters": ["52:54:00:12:34:56", "192.168.1.51", "Microsoft Print to PDF"],
  "users": [
    {
      "user": "MADANIYAT\\e.turdiyev",
      "limit": -1,
      "used": 137,
      "allowedPrinters": ["52:54:00:12:34:56", "192.168.1.51", "Microsoft Print to PDF"]
    },
    { "user": "a.karimov", "limit": -1, "used": 12, "allowedPrinters": ["*"] },
    { "user": "b.aliyev", "limit": 0, "used": 3, "allowedPrinters": [] },
    { "user": "d.rahimov", "limit": -1, "used": 0, "allowedPrinters": null }
  ]
}
```

`users[]` da agent so'ramagan loginlar ham bo'ladi. Ularni ham keshga yozing: shu odam keyin
shu kompyuterga kirishi mumkin.

### Qiymatlarning ma'nosi

| `allowedPrinters` | Agent nima qiladi |
| --- | --- |
| `["*"]` | barcha printerlar ruxsat |
| `[]` | hech qaysi printerdan chiqarmaydi |
| nishonlar ro'yxati | faqat shu printerlar ruxsat |
| `null` yoki maydon yo'q | shu daraja uchun server fikr bildirmagan, keyingi darajaga o'tiladi |

### Qaysi ro'yxat qo'llanadi

1. `users[]` dagi aynan shu xodim qatorining `allowedPrinters` qiymati.
2. U `null` bo'lsa yoki xodim ro'yxatda bo'lmasa, javobning yuqori qismidagi `allowedPrinters`.
3. U ham bo'lmasa, cheklov qo'llanmaydi.

Bu `limit` va `defaultLimit` bilan bir xil mantiq.

Xodim qatorini topishda ikki tomon ham bir xil ko'rinishga keltiriladi: oxirgi `\` dan
keyingi qism, kichik harfda. Server so'ralgan login uchun agent yuborgan shaklni qaytaradi
(`MADANIYAT\E.Turdiyev`), so'ralmagani uchun qisqa shaklni (`e.turdiyev`).

### Nishon nima

Ro'yxat elementi MAC, IPv4 yoki printer nomi bo'ladi. Turi alohida ko'rsatilmaydi.

| Printer turi | Ro'yxatda nima keladi |
| --- | --- |
| Tarmoq printeri | MAC va joriy IP. Nom kelmaydi: bir xil nom turli printerlarda uchraydi |
| USB printer | nom, faqat admin ruxsat bergan bo'lsa |
| Virtual printer (PDF va boshqalar) | nom, faqat admin ro'yxatga qo'shgan bo'lsa |

Nom agent `printer` maydonida yuboradigan qiymatning aynan o'zi bo'ladi. Virtual printerlar
uchun alohida qoida yozmang: ular ham oddiy nishon sifatida tekshiriladi.

## Ruxsatni tekshirish

Tekshiruv ish navbatga tushganda, mavjud kvota tekshiruvidan keyin, xuddi shu joyda bajariladi:

1. Xodimning `limit` qiymati `0` bo'lsa, ish to'siladi. Bu bugungi mantiq, o'zgarmaydi.
2. `allowedPrinters` shu printerga ruxsat bermasa, ish to'siladi.
3. Aks holda ish chiqadi.

Printerning uchta qiymati **ish chiqishidan oldin** aniqlanadi. Bittasi ro'yxatga mos kelsa,
ruxsat beriladi. Hech biri mos kelmasa, ish to'siladi.

| Qiymat | Qayerdan olinadi | Eslatma |
| --- | --- | --- |
| Nom | `Win32_Printer.Name` | `printer` maydonidagi qiymat bilan bir xil |
| IP | Standard TCP/IP port: `Win32_TCPIPPrinterPort.HostAddress`, xost nomi bo'lsa DNS orqali IPv4 | `USB001`, `WSD-...`, `nul:` IP emas, bo'sh qoldiring |
| MAC | ARP jadvali yoki SNMP | Topilmasa bo'sh. Oddiy holatda IP mos kelgani yetarli |

**Ulashilgan printer** (`\\server\printer`) va manzili aniqlanmagan boshqa navbatlar faqat
nom bo'yicha tekshiriladi va nom ro'yxatda bo'lmasa to'siladi. Bu ataylab shunday: aks holda
hamkasbning kichik printerini ulashib, cheklovni chetlab o'tish mumkin bo'lardi.

Normalizatsiya:

- **MAC:** faqat o'n oltilik raqamlar qoldiriladi, katta harfga o'tkaziladi. Server MAC'ni
  `52:54:00:12:34:56` ko'rinishida yuboradi.
- **IP:** bo'sh joylar kesiladi, aynan taqqoslanadi.
- **Nom:** bo'sh joylar kesiladi, harf registri hisobga olinmaydi.

```csharp
static string NormalizeMac(string? v) =>
    v is null ? "" : new string(v.Where(Uri.IsHexDigit).ToArray()).ToUpperInvariant();

/// <summary>allowed == null: server fikr bildirmagan, cheklov yo'q.</summary>
static bool IsPrinterAllowed(
    IReadOnlyList<string>? allowed,
    string? printerMac,
    string? printerIp,
    string printerName)
{
    if (allowed is null) return true;
    if (allowed.Any(a => a == "*")) return true;
    if (allowed.Count == 0) return false;

    var mac = NormalizeMac(printerMac);
    var ip = printerIp?.Trim() ?? "";
    var name = printerName?.Trim() ?? "";

    foreach (var raw in allowed)
    {
        var token = raw?.Trim();
        if (string.IsNullOrEmpty(token)) continue;

        if (mac.Length == 12 && NormalizeMac(token) == mac) return true;
        if (ip.Length > 0 && string.Equals(token, ip, StringComparison.Ordinal)) return true;
        if (name.Length > 0 && string.Equals(token, name, StringComparison.OrdinalIgnoreCase)) return true;
    }

    return false;
}
```

Bu namuna kompilyatsiya qilib tekshirilmagan, mantiq uchun berilgan.

### Chekka holatlar

| Holat | Agent nima qiladi |
| --- | --- |
| Server bilan aloqa yo'q | Oxirgi muvaffaqiyatli javobdagi ro'yxat ishlatiladi |
| Agent qayta ishga tushdi | Ro'yxat diskdagi keshdan olinadi |
| Birorta ham javob olinmagan | Cheklamaydi. Aloqa uzilgani uchun idora to'xtab qolmasligi kerak |
| Ro'yxat kutilmagan ko'rinishda (massiv emas, ichida raqam) | Cheklamaydi, jurnalga ogohlantirish yozadi |
| `periodKey` o'zgardi | Faqat hisoblagichlar nolga tushadi, ro'yxatga ta'sir qilmaydi |
| Kompyuterda bir necha foydalanuvchi | Mashinaning emas, chop etayotgan xodimning ro'yxati qo'llanadi |

### Sozlamalar

| Kalit | Qiymat | Nima uchun |
| --- | --- | --- |
| `EnablePrintQuotas` | `true` | `allowedPrinters` shu kanal orqali keladi |
| `CancelJobsOverQuota` | `true` | To'sish mexanizmi yoqilgan bo'lishi kerak |
| `QuotaSyncIntervalMinutes` | `1` | Admin ro'yxatni o'zgartirsa, agent bir daqiqada biladi |

## To'silgan ish

Ish printerga ketmasdan bekor qilinadi va `POST /api/print-jobs` ga mavjud shaklda yuboriladi:

```json
{
  "user": "MADANIYAT\\e.turdiyev",
  "document": "Buyruq loyihasi.docx",
  "printer": "Kyocera M2040dn",
  "printerIp": "192.168.1.52",
  "printerMac": "52:54:00:12:34:58",
  "pages": 0,
  "timestamp": "2026-11-09T09:16:02.1234567+05:00",
  "success": false,
  "reason": "Canceled by printer policy: this printer is not allowed for this user"
}
```

- `reason` aynan shu matn bo'lsin, boshqa variantlarsiz. Server urinishlarni shu matn
  bo'yicha ajratadi.
- `pages` albatta `0` bo'lsin: server sarfni `pages` yig'indisidan hisoblaydi.
- Bitta to'silgan ish uchun bitta yozuv yuboriladi. Bekor qilishdan keyin spooler beradigan
  ikkinchi hodisa alohida yozuv bo'lib ketmasin.

**Foydalanuvchiga xabar** mavjud kvota to'sig'idagi usulda chiqadi, matni:

> Bu printerdan chop etishga ruxsatingiz yo'q. Umumiy foydalanish uchun belgilangan
> printerlardan birini tanlang.

## MAC manzil

`printerMac` serverda printerni tanib olishning asosiy kaliti, shuning uchun noto'g'ri MAC
bo'sh MAC'dan ancha yomon.

**Muammo o'lchangan.** Serverdagi 29 ta MAC'dan 15 tasi printerga tegishli bo'lmagan.
Printerlarning IP'si ko'chgan, eski IP'ni IP-telefonlar egallagan, kompyuterda esa eski
navbat qolgan. Agent shu navbatga chop etishda ARP'dan telefon MAC'ini olib yuborgan. Bunday
yozuvlar qo'lda tozalandi, lekin sabab qolgan.

**Qoida.** Ish hodisasida `printerMac` faqat quyidagi holda yuboriladi, aks holda `null`:

1. Ish muvaffaqiyatli chiqqan (`success: true`). Telefon chop etishni qabul qilmaydi, shuning
   uchun bu shart soxta MAC'larning deyarli hammasini kesadi.
2. Printer ulashilgan navbat emas. `\\server\printer` da ARP chop etish serverining MAC'ini
   beradi va o'sha serverdagi barcha printerlar bitta qurilma bo'lib qoladi.

Yuqoridagi ruxsat tekshiruvi uchun ARP qiymati ish chiqishidan oldin ham ishlatilaveradi. Bu
qoida faqat serverga yuboriladigan yozuvga tegishli.

Format muhim emas: server `52-54-00-12-34-56`, `525400123456` va `5254.0012.3456` ni bir xil
ko'rinishga keltiradi. USB printerda MAC bo'lmaydi, bu normal.

## Ortiqcha yozuvlar

Bu tavsiya, sarf hisobiga ta'sir qilmaydi.

4-chorakda "Print job was canceled or deleted before completing" sababli 3 186 ta yozuv bor,
birortasida varaq yo'q. Ularning 3 127 tasida (98%) ayni hujjat shu kompyuterdan 10 daqiqa
ichida muvaffaqiyatli chiqqan. Ko'pchiligining hujjat nomi `Печать документа`. Eng ko'p
tarmoqdagi Canon printerlarda uchraydi.

Bitta chop etish ikki yozuv bo'lib ketayotganga o'xshaydi. Shu sababli dashboardda
muvaffaqiyat darajasi 69% ko'rinmoqda. Sababini aniqlang va ortiqcha yozuv bo'lsa, yubormang.
Foydalanuvchi haqiqatan bekor qilgan ishlar yozilishda davom etsin.

## Sinash

Agentni haqiqiy serverda boshqa xodimlarga ta'sir qilmasdan sinash mumkin. Admin sinov
loginini dashboardda "Ma'lum printerlar" guruhiga qo'shadi. Cheklov o'chiq turganda ham shu
login uchun javobda aniq ro'yxat keladi, qolganlarga `["*"]` ketaveradi.

Topshirishdan oldin tekshiring:

- [ ] `["*"]`: barcha printerlardan chiqadi
- [ ] Maydon yo'q yoki `null`: yuqori qismdagi ro'yxat, u ham yo'q bo'lsa cheklovsiz
- [ ] `[]`: hech qaysi printerdan chiqmaydi
- [ ] Ro'yxatda MAC bor va printerning MAC'i mos: chiqadi
- [ ] Ro'yxatda `52-54-00-12-34-56`, printerda `52:54:00:12:34:56`: chiqadi
- [ ] MAC topilmadi, lekin IP ro'yxatda bor: chiqadi
- [ ] Ro'yxatda `kyocera m2040dn`, printer nomi `Kyocera M2040dn`: chiqadi
- [ ] Hech bir nishon mos kelmaydi: ish printerga bormasdan bekor qilinadi
- [ ] `\\server\printer` navbati, nomi ro'yxatda yo'q: to'siladi
- [ ] USB printer, nomi ro'yxatda yo'q: to'siladi
- [ ] `Microsoft Print to PDF` ro'yxatda bor: chiqadi, yo'q: to'siladi
- [ ] To'silgan ish `success: false`, `pages: 0` va aynan belgilangan `reason` bilan bitta
      yozuv bo'lib keladi
- [ ] Foydalanuvchi sababni ko'radi
- [ ] Ikki xodimga ikki xil ro'yxat: har biri o'z ro'yxati bilan cheklanadi
- [ ] `MADANIYAT\E.Turdiyev` javobdagi `e.turdiyev` qatoriga mos keladi
- [ ] Server o'chiq: oxirgi ro'yxat ishlatiladi
- [ ] Agent qayta ishga tushdi, server o'chiq: keshdagi ro'yxat ishlatiladi
- [ ] Hech qachon javob olinmagan: cheklanmaydi
- [ ] `[123]` kabi noto'g'ri qiymat: cheklanmaydi, jurnalga yoziladi
- [ ] `periodKey` o'zgardi: hisoblagich nolga tushdi, ro'yxat o'zgarmadi
- [ ] Muvaffaqiyatsiz ishda va ulashilgan navbatda `printerMac` yuborilmaydi
- [ ] `/api/agent-status` da yangi versiya raqami ko'rinadi

## Chiqarish tartibi

1. Yangi versiya bir-ikki kompyuterda sinov logini bilan tekshiriladi.
2. Versiya barcha kompyuterlarga tarqatiladi. Cheklov o'chiq, hammaga `["*"]` ketadi, shuning
   uchun hech narsa o'zgarmaydi.
3. Admin dashboardning Agentlar sahifasida yangi versiya tarqalganini ko'radi va cheklovni
   yoqadi.

Yangilanmagan kompyuterlar cheklamaydi, lekin sarf hisobi ularda ham to'g'ri ishlaydi. Server
qaysi agent ro'yxatni qo'llayotganini versiya raqamidan biladi, shuning uchun versiyani oshirish
majburiy.

Muammo chiqsa, admin cheklovni o'chiradi va agentlar bir daqiqa ichida `["*"]` oladi. Agentni
qaytarib o'rnatish shart emas.

## Ma'lumot uchun

Asosiy manzil: `https://print.madaniyhayot.uz`. Barcha so'rovlar `X-Api-Key` sarlavhasi bilan.

| Endpoint | Vazifa | Shu ishda o'zgaradimi |
| --- | --- | --- |
| `POST /api/print-jobs` | Chop etish hodisalari paketi | Shakli yo'q, `printerMac` qoidasi o'zgaradi |
| `POST /api/print-quotas` | Sarfni bildirish va ruxsatlarni olish | Yo'q, `allowedPrinters` javobda bor |
| `POST /api/agent-status` | Tiriklik signali | Yo'q, yangi versiya raqami yuboriladi |

Bitta paketda eng ko'pi 60 000 hodisa. Paketdagi bitta noto'g'ri hodisa (masalan, manfiy
`pages`) butun paketni rad ettiradi (`422`), shuning uchun yuborishdan oldin maydonlarni
tekshiring.

Noaniq joy bo'lsa yoki boshqa yondashuv qulayroq bo'lsa, yozing: server tomonini moslashtirish
mumkin.
