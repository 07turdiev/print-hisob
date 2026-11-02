# Printer Hisob — agent uchun o'zgarishlar (PrintMonitor.exe)

Hujjat sanasi: 2026-11-02 · Madaniy Hayot

## Qisqa xulosa

Agentda ikkita majburiy o'zgarish va ikkita tavsiya bor. Asosiysi — serverdan keladigan
`allowedPrinters` ro'yxatini qo'llash: xodim faqat o'ziga ruxsat etilgan printerlardan
chiqara olishi kerak.

To'sish qarorini **agent** qabul qilishi kerak, chunki ish navbatga tushgan va printer
qog'ozni tortgan payt orasida millisekundlar bor. Server faqat ro'yxatni yetkazadi.

| O'zgarish | Majburiylik | Hujjatdagi bo'limi |
| --- | --- | --- |
| Javobdagi `allowedPrinters` ro'yxatini qo'llash | majburiy | 2-o'zgarish |
| `appsettings.json` da `QuotaSyncIntervalMinutes: 1` | majburiy | 3-o'zgarish |
| `printerMac` ni hozir bo'sh ketayotgan holatlarda ham to'ldirish | tavsiya | 1-o'zgarish |
| Yangi `printerPort` maydonini yuborish | tavsiya | 1-o'zgarish |

Server tomoni orqaga mos: yangi maydon qo'shilgandan keyin ham eski agentlar avvalgidek
ishlaydi. Shuning uchun server oldin chiqariladi, agent keyin yangilanadi — flotdagi
189 ta mashinani bir vaqtda yangilash shart emas.

Serverning asosiy manzili: `https://print.madaniyhayot.uz`. Endpointlar va
autentifikatsiya o'zgarmaydi.

## Server printerni qanday aniqlaydi

Serverda printerlar reyestri ishga tushdi: har bir jismoniy printer bazada bitta yozuv,
admin unga o'zi nom qo'yadi ("3-qavat, kotibiyat"). Jurnalda va hisobotlarda drayver nomi
emas, shu nom ko'rinadi.

Agent yuborgan har bir yozuv uchta nishondan biri bo'yicha qurilmaga bog'lanadi — aynan
shu tartibda:

1. `printerMac` — bor bo'lsa, asosiy kalit.
2. `printerIp` — haqiqiy IPv4 bo'lsa. Port nomlari (`USB001`, `WSD-a1b2…`, `nul:`) nishon
   sifatida qabul qilinmaydi: ular har bir kompyuterda boshqa printerni bildiradi.
3. `printer` — drayver nomi. Faqat MAC ham, IP ham bo'lmaganda ishlatiladi.

Nishon bir marta qurilmaga bog'langach, o'sha qurilmada qoladi. Shuning uchun bitta
printer turli kompyuterlarda "HP LaserJet M404", "HP LaserJet MFP M428" va "Kotibiyat
printeri" deb atalgan bo'lsa ham, MAC yoki IP bir xil bo'lsa — bazada bitta qator.

Agentda bu qism uchun kod o'zgarishi kerak emas: `printer`, `printerIp`, `printerMac`
maydonlari allaqachon yuborilayapti va ularning ma'nosi o'zgarmadi.

## 1-o'zgarish — `printerMac` ni to'ldirish (tavsiya)

**Joriy holat — o'lchangan.** 2026-yil 2-noyabr holatiga ko'ra bazadagi 28 443 yozuvdan
11 754 tasida (41%) `printerMac` bor, va ularning hammasi to'g'ri formatda keladi. Ya'ni
agent MAC ni allaqachon yuborayapti — lekin hamma holatda emas.

MAC bir printerga tegishli ekani tasdiqlandi: bitta MAC 16 ta kompyuterda, 1 ta IP bilan,
11 xil drayver nomi ostida ko'rinadi. Aynan shu narsa bitta printerni bazada bir necha
qator qilib ajratib yuborgan.

Qolgan 16 689 yozuvda (59%) MAC yo'q, va sababi ikki xil:

| MAC siz yozuvlar | Soni | Nima ko'rinadi | Ehtimoliy sabab |
| --- | --- | --- | --- |
| Port ham bo'sh | 11 329 | `printerIp` bo'sh, 80 xil nom | Ulashilgan (`\\server\printer`) yoki mahalliy printer — agent port haqida hech narsa yubormayapti |
| Haqiqiy IP bor | 5 360 | `192.168.20.x`, `192.168.30.x` | Agent MAC ni aniqlay olmagan — printer boshqa pod-tarmoqda bo'lsa ARP ishlamaydi |

Kompyuterlar kesimi: 6 ta mashina MAC ni doim yuboradi, 88 tasi ba'zan, 34 tasi hech
qachon. Demak muammo agent versiyasida emas — bitta mashina bir printerga MAC bilan,
boshqasiga MAC siz yozadi.

**Buning narxi:** 29 ta jismoniy printer bazada 114 ta qurilma bo'lib yotibdi (80 tasi
faqat nom bo'yicha aniqlangan). Hisobotlar shuning uchun bo'linib ketgan.

**Nima uchun kerak:** DHCP IP ni almashtirsa yoki printer boshqa pod-tarmoqqa ko'chsa,
server uni yangi qurilma deb biladi — statistika ikkiga bo'linadi va admin ularni qo'lda
birlashtirishi kerak bo'ladi. MAC esa o'zgarmaydi.

**Format muhim emas.** Server qabul qilishdan oldin o'zi normallashtiradi — quyidagilarning
hammasi bir xil printer sifatida tushadi:

```
52:54:00:12:34:56
52-54-00-12-34-56
525400123456
5254.0012.3456
```

Saqlanadigan ko'rinish: katta harf, ikki nuqta bilan (`52:54:00:12:34:56`). 12 ta onalik
raqamga keltirib bo'lmaydigan qiymat o'z holida saqlanadi, hech narsa buzilmaydi. Maydon
uzunligi — 64 belgigacha.

**Qanday olish mumkin** (tarmoq printerlari uchun):

- `Win32_TCPIPPrinterPort` → port IP si → ARP jadvali (`GetIpNetTable`, yoki oddiy
  `arp -a`) → MAC;
- yoki printerning SNMP `ifPhysAddress` qiymati (OID `1.3.6.1.2.1.2.2.1.6`);
- USB printerlarda MAC yo'q — bu normal, maydon bo'sh qolsa server IP yoki nom bo'yicha
  ishlaydi.

**Muhim — MAC aynan printerning o'zi bo'lishi kerak.** Noto'g'ri MAC bo'sh MAC dan ancha
yomon: bir xil MAC bilan kelgan printerlar bazada bitta qurilmaga qo'shilib ketadi va buni
keyin ajratib bo'lmaydi.

- Printer `\\server\printer` ko'rinishida ulashilgan bo'lsa, ARP chop etish serverining
  MAC'ini beradi — natijada o'sha serverdan ulashilgan **barcha** printerlar bitta qurilma
  bo'lib qoladi. Bunday holatda MAC yubormaslik kerak.
- ARP jadvali faqat bir xil pod-tarmoqdagi qurilmalarni biladi. Printer router orqasida
  bo'lsa yozuv topilmaydi — bu yerda SNMP ishlaydi.
- Shubha bo'lsa `null` yuborilsin. Tizim IP va nom bilan ishlashda davom etadi.

MAC keyinchalik o'zgarishi mumkin (tarmoq platasi almashtirilgan, printer kabeldan Wi-Fi ga
o'tgan) — bu muammo emas: server printerni yangi qurilma deb biladi va admin ikkisini
`merge` bilan birlashtiradi. Agent tomonida hech narsa qilish kerak emas, faqat qanday MAC
ko'rinsa shuni yuborsin.

### Qo'shimcha so'rov — `printerPort`

MAC siz yozuvlarning ko'pchiligida (11 329 ta) `printerIp` ham bo'sh. Bunday yozuvda
printerni ajratish uchun faqat drayver nomi qoladi — eng ishonchsiz nishon, chunki har
kompyuterda boshqacha.

Shuning uchun yangi ixtiyoriy maydon so'raymiz: `printerPort` — `Win32_Printer.PortName`
qiymati, qanday bo'lsa shundayligida.

```json
{ "printer": "HP LaserJet M404", "printerPort": "IP_192.168.20.93" }
```

Bu juda qimmatli, chunki Windows'dagi TCP/IP port nomi ko'pincha printerning IP sini
o'zida saqlaydi (`IP_192.168.20.93`), ulashilgan printerda esa barqaror yo'lni beradi
(`\\SERVER\HP-3qavat`). Ikkisi ham drayver nomidan ancha ishonchli.

Server tomoni bu maydonni qabul qilishga tayyorlanadi. Agent uchun ish hajmi kichik:
qiymat `Win32_Printer` dan to'g'ridan-to'g'ri olinadi, hech narsa hisoblash kerak emas.

MAC topilmasa `null` yoki bo'sh satr yuborilsa bo'ladi — ikkisi ham `NULL` sifatida
yoziladi. Bu o'zgarish majburiy emas: ishlab turgan tizim MAC siz ham to'g'ri ishlaydi,
faqat IP almashganda qo'l mehnati paydo bo'ladi.

## 2-o'zgarish — `allowedPrinters` (asosiy ish)

Mavjud `POST /api/print-quotas` javobiga bitta yangi maydon qo'shiladi. Endpoint,
autentifikatsiya va so'rov tanasi o'zgarmaydi.

**So'rov** (hozirgidek, o'zgarish yo'q):

```json
{
  "computer": "LAPTOP-JANE",
  "periodKey": "2026-Q4",
  "timestamp": "2026-11-02T09:15:00Z",
  "users": [
    { "user": "MADANIYAT\\e.turdiyev", "pagesUsedHere": 42, "pagesUsed": 137, "limit": -1 }
  ]
}
```

**Javob** (`allowedPrinters` — yangi, ikki joyda):

```json
{
  "periodKey": "2026-Q4",
  "defaultLimit": -1,
  "allowedPrinters": ["*"],
  "users": [
    {
      "user": "e.turdiyev",
      "limit": -1,
      "used": 137,
      "allowedPrinters": ["52:54:00:12:34:56", "192.168.1.51"]
    }
  ]
}
```

### Qiymatlarning ma'nosi

| Qiymat | Agent nima qiladi |
| --- | --- |
| maydon yo'q yoki `null` | cheklamaydi — "serverda bu haqda fikr yo'q" |
| `["*"]` | barcha printerlar ruxsat |
| `[]` (bo'sh ro'yxat) | hech qaysi printerdan chiqarmaydi |
| nishonlar ro'yxati | faqat shu printerlar ruxsat |

### Ustunlik tartibi

1. `users[].allowedPrinters` — shu foydalanuvchi uchun aniq ro'yxat;
2. yuqoridagi umumiy `allowedPrinters` — ro'yxatda alohida ko'rsatilmagan hammaga;
3. ikkisi ham yo'q — cheklov qo'llanmaydi.

Bu `limit` va `defaultLimit` bilan to'liq bir xil mantiq, shuning uchun mavjud kodga
qo'shib ketish oson bo'lishi kerak.

### Nishon nima bo'lishi mumkin

Ro'yxat elementi — MAC, IPv4 yoki printer nomi. Uchalasi aralash kelishi mumkin:

```json
"allowedPrinters": ["52:54:00:12:34:56", "192.168.1.51", "Kyocera M2040dn"]
```

Sabab: tarmoqdagi printerlarning bir qismida MAC bor, bir qismida faqat IP, USB
printerlarda esa faqat nom. Server adminga qaysi nishon bor bo'lsa, shuni yuboradi.

## Taqqoslash algoritmi

Ish navbatga tushganda agent shu printerning uchta nishonini ro'yxat bilan taqqoslaydi.
**Bittasi mos kelsa — ruxsat.** Hammasi mos kelmasa — to'sadi.

Normalizatsiya qoidalari:

- **MAC** — harf-raqamdan boshqa belgilar olib tashlanadi, katta harfga o'tkaziladi. Ya'ni
  `52-54-00-12-34-56`, `525400123456` va `52:54:00:12:34:56` bir xil hisoblanadi.
- **IP** — bo'sh joylar kesiladi, aynan taqqoslanadi.
- **Nom** — bo'sh joylar kesiladi, harf registri hisobga olinmaydi (`OrdinalIgnoreCase`).

Namuna:

```csharp
static string NormalizeMac(string? v) =>
    v is null ? "" : new string(v.Where(Uri.IsHexDigit).ToArray()).ToUpperInvariant();

/// <summary>
/// `allowedPrinters` ro'yxati shu printerga ruxsat beradimi.
/// null — serverda fikr yo'q, cheklov qo'llanmaydi.
/// </summary>
static bool IsPrinterAllowed(
    IReadOnlyList<string>? allowed,
    string? printerMac,
    string? printerIp,
    string printerName)
{
    if (allowed is null) return true;                 // fikr yo'q
    if (allowed.Any(a => a == "*")) return true;      // hammasi ruxsat
    if (allowed.Count == 0) return false;             // hech qaysi

    var mac = NormalizeMac(printerMac);
    var ip = printerIp?.Trim() ?? "";
    var name = printerName?.Trim() ?? "";

    foreach (var raw in allowed)
    {
        var token = raw?.Trim();
        if (string.IsNullOrEmpty(token)) continue;

        if (mac.Length > 0 && NormalizeMac(token) == mac) return true;
        if (ip.Length > 0 && string.Equals(token, ip, StringComparison.Ordinal)) return true;
        if (name.Length > 0 && string.Equals(token, name, StringComparison.OrdinalIgnoreCase)) return true;
    }

    return false;
}
```

E'tibor bering: `NormalizeMac(token)` nishonning o'zini ham normallashtiradi — shunda
ro'yxatda MAC qanday yozilgan bo'lsa ham ishlaydi. IP nishoni MAC bilan taqqoslanganda
bo'sh satrga aylanadi, shuning uchun noto'g'ri moslik chiqmaydi (`mac.Length > 0` sharti
ham shu uchun turibdi).

## To'sish va serverga hisobot

Qaror tartibi — mavjud kvota tekshiruvidan keyin, xuddi shu joyda:

1. Foydalanuvchining `limit` qiymati `0` bo'lsa — to'sish (bu allaqachon ishlab turgan
   mantiq, o'zgarmaydi).
2. `allowedPrinters` shu printerga ruxsat bermasa — to'sish.
3. Aks holda — chiqarishga ruxsat.

**Yangi ingest maydoni kerak emas.** To'sgan ishni mavjud shaklda yuborish yetarli —
`POST /api/print-jobs`:

```json
{
  "user": "MADANIYAT\\e.turdiyev",
  "document": "Buyruq loyihasi.docx",
  "printer": "Kyocera M2040dn",
  "printerIp": "192.168.1.52",
  "printerMac": "52:54:00:12:34:58",
  "pages": 0,
  "timestamp": "2026-11-02T09:16:02.1234567+05:00",
  "success": false,
  "reason": "Printer ruxsat etilmagan (guruh siyosati)"
}
```

`reason` matni serverda alohida hisobotga tushadi — "qaysi xodim qaysi ruxsatsiz
printerdan chiqarishga urindi". Shuning uchun matnni **barqaror** saqlash kerak: bitta
aniq ibora bo'lsin, har xil variantlar bilan yozilmasin. Tavsiya etilgan matn aynan
yuqoridagi: `Printer ruxsat etilmagan (guruh siyosati)`.

`pages: 0` bo'lishi kerak — qog'oz sarflanmagani uchun. `success: false` yozuv sarf
hisobiga kirmaydi, lekin jurnalda ko'rinadi.

**Foydalanuvchiga xabar:** hozirgi kvota to'sig'idagi mexanizm qanday bo'lsa, shunday
qoldirilsin (tray xabari yoki shunga o'xshash). Matnda sabab aytilishi muhim — avval
odamlar nima uchun chiqmaganini bilmay qolgan. Tavsiya: "Bu printerdan chiqarishga
ruxsatingiz yo'q. Ruxsat etilgan printerlar ro'yxatini ma'muriyatdan so'rang."

## Chekka holatlar

### Server bilan aloqa yo'q

**Oxirgi muvaffaqiyatli javobdagi ro'yxat ishlatiladi** — `limit` bilan bir xil yondashuv.
Agent qayta ishga tushganda ham ro'yxat saqlanib turishi kerak (diskdagi kesh).

Agent hali birorta javob olmagan bo'lsa (yangi o'rnatilgan mashina, server o'chiq) —
**cheklamaydi**. Sababi amaliy: aloqa uzilgani uchun butun idorani chiqarishdan to'xtatib
qo'yish kvota tizimining o'zidan ko'proq zarar keltiradi. Bu ongli qaror, xato emas.

### `periodKey` o'zgarishi

`periodKey` faqat hisoblagichlarni nolga tushiradi. **`allowedPrinters` ga ta'sir
qilmaydi** — ro'yxat davrga bog'liq emas, u faqat yangi javob kelganda yangilanadi.

### Ro'yxat qisqarganda

Admin printerni ro'yxatdan chiqarsa, agent buni keyingi sinxronizatsiyada biladi. Shu
sababli `QuotaSyncIntervalMinutes: 1` kerak — aks holda o'zgarish 5–10 daqiqa kechikadi.

### Noto'g'ri yoki tushunarsiz qiymat

Javobda `allowedPrinters` kutilmagan ko'rinishda kelsa (massiv emas, ichida raqam bor va
hokazo) — **cheklamaslik** va jurnalga ogohlantirish yozish. Serverdagi xato tufayli chop
etish to'xtab qolmasligi kerak.

### Bir mashinada bir necha foydalanuvchi

Ro'yxat har bir login uchun alohida. Agent `users[]` dan aynan chop etayotgan
foydalanuvchini topib, uning ro'yxatini qo'llashi kerak — mashinaning emas.

Login taqqoslashda domen prefiksi hisobga olinmaydi: server `MADANIYAT\E.Turdiyev` ni
`e.turdiyev` ga keltirib javob qaytaradi. Agent ham shu qoida bilan solishtirishi kerak —
oxirgi `\` dan keyingi qism, kichik harfda.

## 3-o'zgarish — `appsettings.json`

| Kalit | Qiymat | Nima uchun |
| --- | --- | --- |
| `EnablePrintQuotas` | `true` | Kvota almashinuvi yoqilgan bo'lishi kerak — `allowedPrinters` shu kanal orqali keladi |
| `CancelJobsOverQuota` | `true` | To'sish mexanizmi yoqilgan bo'lsin |
| `QuotaSyncIntervalMinutes` | `1` | Admin ro'yxatni o'zgartirganda agent 1 daqiqada biladi |

`QuotaSyncIntervalMinutes: 1` yuk tug'dirmaydi — o'lchab chiqilgan: bitta almashinuv
≈ 416 bayt, 189 mashina 1 daqiqalik interval bilan sekundiga 3,1 so'rov va bir mashinaga
kuniga ≈ 585 KB. Server uchun bu sezilarsiz.

Boshqa sozlamalar o'zgarmaydi.

## Chiqarish tartibi

1. **Server** — `allowedPrinters` javobga qo'shiladi, boshida hamma uchun `["*"]` (ya'ni
   hech kim cheklanmaydi). Eski agentlar notanish maydonni e'tiborsiz qoldiradi, shuning
   uchun flotda hech narsa o'zgarmaydi.
2. **Agent** — yangi versiya tayyorlanadi va bir-ikki mashinada sinaladi.
3. **Guruhlar** — admin dashboardda birinchi guruhni tuzadi; faqat shundan keyin haqiqiy
   cheklov boshlanadi.

Ya'ni agentni butun flotga bir vaqtda yoyish shart emas: yangilanmagan mashinalar
oddiygina cheklamaydi, lekin sarf hisobi ularda ham to'g'ri ishlaydi.

Teskari tomoni ham ishlaydi — agar yangi agent muammo chiqarsa, serverda umumiy
`allowedPrinters` ni `["*"]` ga qaytarish kifoya; agentni qaytarib o'rnatish kerak emas.

## Qabul testlari

Topshirishdan oldin shu holatlar tekshirilsin:

- [ ] `allowedPrinters: ["*"]` — barcha printerlardan chiqadi
- [ ] Maydon umuman yuborilmadi — barcha printerlardan chiqadi (eski xatti-harakat)
- [ ] `allowedPrinters: []` — hech qaysi printerdan chiqmaydi
- [ ] Ro'yxatda MAC bor, printerning MAC si mos — chiqadi
- [ ] Ro'yxatda MAC `52-54-00-12-34-56` ko'rinishida, printerda `52:54:00:12:34:56` —
      chiqadi (normalizatsiya ishlayapti)
- [ ] Ro'yxatda faqat IP bor, printerda MAC ham bor — IP mos kelsa chiqadi
- [ ] Ro'yxatda printer nomi `kyocera m2040dn` (kichik harfda), printerda
      `Kyocera M2040dn` — chiqadi
- [ ] Ro'yxatdagi hech bir nishon mos kelmaydi — ish bekor qilinadi
- [ ] Bekor qilingan ish serverga `success: false`, `pages: 0`, barqaror `reason` bilan
      yuboriladi
- [ ] Foydalanuvchi ekranida sabab ko'rinadigan xabar chiqadi
- [ ] `users[]` da ikki login bor, har biriga boshqa ro'yxat — har biri o'z ro'yxati bilan
      cheklanadi
- [ ] `MADANIYAT\E.Turdiyev` bilan kirgan foydalanuvchi javobdagi `e.turdiyev` qatoriga
      to'g'ri moslanadi
- [ ] Serverga aloqa uzildi — oxirgi ro'yxat ishlatiladi
- [ ] Agent qayta ishga tushdi, server o'chiq — keshdagi ro'yxat ishlatiladi
- [ ] Umuman birorta javob olinmagan — cheklov qo'llanmaydi
- [ ] `allowedPrinters` ichida kutilmagan tur (masalan `[123]`) — cheklanmaydi, jurnalga
      ogohlantirish yoziladi
- [ ] `periodKey` o'zgardi — hisoblagich nolga tushdi, ro'yxat o'zgarmadi
- [ ] MAC to'ldirilayotgan bo'lsa: tarmoq printerida MAC bor, USB printerida bo'sh —
      ikkisi ham xatosiz yuboriladi

## Ma'lumot uchun — agent ishlatadigan endpointlar

Asosiy manzil: `https://print.madaniyhayot.uz`. Hammasi `Bearer` token bilan, o'zgarish
yo'q.

| Endpoint | Vazifa | Shu ishda o'zgaradimi |
| --- | --- | --- |
| `POST /api/print-jobs` | Chop etish hodisalari paketi | Shakli o'zgarmaydi (`printerMac` to'liqroq, `printerPort` qo'shilsa yaxshi) |
| `POST /api/print-quotas` | Sarfni bildirish + limitlarni olish | **Ha** — javobga `allowedPrinters` qo'shiladi |
| `POST /api/agent-status` | Tiriklik signali | Yo'q |

Bitta paketdagi hodisalar chegarasi — 60 000. Agentning mahalliy buferi standart holatda
50 000, shuning uchun uzilishdan keyin butun bufer bitta paketda yuborilsa ham o'tadi.

### Savollar

Shartnomada tushunarsiz joy bo'lsa yoki boshqa yondashuv qulayroq ko'rinsa — yozib
yuboring, server tomonini moslashtirish mumkin. Ayniqsa quyidagilar muhokamaga ochiq:

- nishon turini aniq ko'rsatish kerak bo'lsa (`{"kind": "mac", "value": "…"}` ko'rinishida)
  — server shunday ham yubora oladi;
- ro'yxat juda uzun bo'lib ketsa (yuzlab printer) — "man etilganlar" ro'yxatiga o'tish
  mumkin.
