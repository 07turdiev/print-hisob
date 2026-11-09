# Printer Hisob: atamalar va hisob qoidalari

Dasturdagi raqam yoki atama haqida savol tug'ilsa, javob shu yerda. Kod shu qoidalarga
mos: `api/app/rules.py` va `api/app/logins.py`.

## Atamalar

| Atama | Ma'nosi | Ishlatilmaydi |
| --- | --- | --- |
| Xodim | AD ro'yxatidagi odam | foydalanuvchi |
| Noma'lum login | Chop etgan, lekin AD ro'yxatida topilmagan login | noma'lum foydalanuvchi |
| Norma | Xodimga davr uchun belgilangan varaq soni. Hech kimni to'xtatmaydi, faqat hisobotda solishtiriladi | kvota, limit |
| Ish | Printerga yuborilgan bitta hujjat | buyurtma, hodisa |
| Chop etish | Hujjatni printerdan chiqarish | chiqarish |
| Bloklash | Xodimning umuman chop eta olmasligi | to'sish |
| Printer | Bitta jismoniy qurilma | qurilma |
| Kompyuter | Agent o'rnatilgan ish joyi | PC, ish stantsiyasi |
| Xato | Printerda haqiqatan bajarilmagan ish | xatolik |
| Bajarilmagan ish | Xato va bekor qilingan ishlar birgalikda | |
| Umumiy printer | Hamma chop eta oladigan printer | |
| Istisno guruhi | Standart qoidadan tashqari ruxsat berilgan xodimlar | |

## Xodim holati

Har bir xodim shu uchta holatdan birida bo'ladi.

| Holat | Qaysi printerlardan chop etadi | Qayerda boshqariladi |
| --- | --- | --- |
| Oddiy | Cheklov yoqilgan bo'lsa faqat umumiy printerlardan | |
| Istisno | Guruhiga qarab barcha printerlardan yoki umumiy va guruhda belgilanganlardan | Guruhlar va ruxsatlar |
| Bloklangan | Hech qaysi printerdan | Xodimlar va normalar |

Bloklash istisnodan ustun turadi. Bir xodim faqat bitta guruhda bo'ladi.

## Qaysi ish hisobga kiradi

Sarf, ish soni va muvaffaqiyat darajasi hamma hisobotda bir xil hisoblanadi.

- **Virtual printerlar kirmaydi.** Nomida pdf, xps, onenote, evernote, fax yoki faks bo'lgan va
  MAC ham, IP ham kelmagan printerlar qog'oz sarflamaydi.
- **Bekor qilingan ishlar kirmaydi.** Varag'i 0 bo'lgan va sababi "Print job was canceled" yoki
  "Canceled by" bilan boshlanadigan ishlar xato ham, sarf ham emas.
- **Jurnalda hammasi ko'rinadi.** Virtual va bekor qilingan ishlar jurnaldan, "Bajarilmagan ishlar
  sababi bo'yicha" panelidan va ruxsat hisobotidan yashirilmaydi.

## KPI va biriktirish

- Biriktirish varaqni ko'chirmaydi. Biriktirilgan xodimning o'z sarfi o'z qatorida qoladi.
- KPI faylidagi va ekrandagi "Jami" ustuni: xodimning o'zi chop etgani va unga biriktirilganlarniki.
  Norma shu songa nisbatan tekshiriladi.
- Shuning uchun KPI ustunini qo'shib chiqilsa, biriktirilgan varaqlar ikki marta sanaladi.
  Haqiqiy qog'oz sarfi jadval ostidagi "Haqiqiy qog'oz sarfi" qatorida turadi.

## Login

Domen prefiksi olib tashlanadi va kichik harfga o'tkaziladi: `MADANIYAT\E.Turdiyev` va
`e.turdiyev` bitta odam. Norma, bloklash, guruh a'zoligi shu ko'rinishda saqlanadi. AD va chop
etish yozuvlaridagi asl yozilish saqlanadi, lekin har doim shu qoida bilan solishtiriladi.

## Printerni tanib olish

1. Yozuv avval MAC, keyin IP bo'yicha printerga bog'lanadi.
2. Nom faqat MAC ham, IP ham kelmaganda ishlatiladi (USB va virtual printerlar).
3. Joriy IP faqat muvaffaqiyatli va eng yangi ishdan yangilanadi.
4. IP o'zgarsa va MAC o'sha bo'lsa, dastur o'zi kuzatadi.
5. MAC o'zgarsa va IP o'sha bo'lsa, chop etish to'xtamaydi, lekin yangi printer qatori paydo
   bo'ladi va uni Printerlar sahifasida eskisiga birlashtirish kerak.

## Davrlar

Oy va chorak chegaralari UTC bo'yicha hisoblanadi. Toshkent vaqti bilan davrning birinchi kuni
soat 05:00 gacha chop etilgan ish oldingi davrga tushadi.
