# AD Sync — xodimlarni Active Directory'dan yuklash

`Sync-AdEmployees.ps1` — AD'dan (`192.168.200.5`, domen `madaniyat.local`) foydalanuvchilarni
o'qib, Printer Hisob API'ga (`POST /api/ad-sync`) yuboradi. Har soatda Task Scheduler orqali ishlaydi.

## Maydonlar moslashuvi

| Backend | AD manbai (standart) | Izoh |
|---|---|---|
| `login` | `sAMAccountName` | Print job'dagi `user` bilan **mos kelishi shart** |
| `fullName` | `DisplayName` (bo'sh bo'lsa `Name`) | F.I.SH. |
| `department` | **OU nomi** (xodim turgan bo'lim) | masalan `Ichki audit bo'limi` |
| `position` | **`Description`** | masalan `Bosh mutaxassis` |
| `active` | **har doim `true`** | AD'da mavjud = ishlayapti (pastga qarang) |

## Ketgan / yangi kelgan xodimlarni aniqlash
AD'dagi `Enabled` bayrog'i **ishlatilmaydi** (bu tashkilotда ko'p akkaunt `Disabled`, lekin
xodimlar ishlayapti). Buning o'rniga **snapshot farqi** ishlatiladi:

- AD'da **bor** → `active: true`
- Oldin bazada bor edi, lekin yangi ro'yxatda **yo'q** → backend uni **`is_active=false`** (ketgan) qiladi
- Yangi login paydo bo'ldi → **yangi kelgan** (upsert)

Bu `Mode: "full"` tufayli avtomatik ishlaydi. Agar kelajakda AD'ning `Enabled` bayrog'i
ishonchli bo'lsa, `config.json` da `"UseAdEnabledFlag": true` qiling.

Sizning AD'ingizda xodimlar **bo'lim nomi bilan atalgan OU'larда** joylashgan va lavozim
**Description** maydoniga yozilgan — shuning uchun standart shunday.

Agar keyinchalik `Department`/`Title` atributlari to'ldirilsa, `config.json` da almashtiring:
```json
"DepartmentSource": "Attribute",   // OU o'rniga AD `department` atributi
"PositionSource":   "Title"        // Description o'rniga AD `title` atributi
```

## Talablar
- **Domenga ulangan Windows mashina**.
- **RSAT / ActiveDirectory moduli**:
  ```powershell
  Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0
  ```
- AD'ni **o'qish** huquqi (oddiy domen foydalanuvchisi yetarli).

## Sozlash
```powershell
cd ad-sync
Copy-Item config.example.json config.json
notepad config.json
```
`config.json` da **`ApiKey`** ni to'ldiring — serverdagi `api/.env` faylidagi `API_KEY`
bilan **bir xil** bo'lishi shart.

> `config.json` da API kalit bor — u `.gitignore` da, repoga tushmaydi.

## 1-qadam: PREVIEW (albatta!)
Hech narsa yubormasdan, AD'dan nima olinayotganini ko'ring:
```powershell
.\Sync-AdEmployees.ps1 -Preview
```
Chiqishda ikki jadval bo'ladi:
1. **Yuboriladigan ko'rinish** — `login / fullName / department / position / active`.
2. **AD xom atributlari** — `OU`, `Department`, `Title`, `Description` yonma-yon.
   Shu jadvaldan qaysi maydon haqiqatan to'ldirilganini ko'rasiz va kerak bo'lsa
   `config.json` dagi manbani o'zgartirasiz.

Tekshiring:
- `department` to'ldirilganmi (bo'sh bo'lsa OU tuzilmasi boshqacha);
- `position` to'g'ri kelganmi ("Bosh mutaxassis" va h.k.);
- `login` print job'lardagi `user` bilan **bir xil formatdami** (domensiz, masalan `iodilov`).

## 2-qadam: Haqiqiy sinxronizatsiya
```powershell
.\Sync-AdEmployees.ps1
```
Javobda `received / upserted / deactivated` ko'rinadi. So'ng dashboard'ning
**Xodimlar** bo'limida ular paydo bo'ladi.

## ⚠️ Muhim: `Mode = "full"` va `MinEmployees`
`full` rejimda backend **payloadda yo'q** xodimlarni `is_active=false` (ketgan) deb belgilaydi.
Bu kerakli xatti-harakat (ketgan xodimlar avtomatik o'chadi), **lekin** AD so'rovi xato ketib
bo'sh ro'yxat qaytarsa — hamma xodim "ketgan" bo'lib qolardi.

Shuning uchun skript **`MinEmployees` dan kam xodim topilsa hech narsa yubormaydi**.
Bu chegarani real xodimlar sonidan pastroq, lekin 0 dan ancha yuqori qiling (masalan 10–50).

## 3-qadam: Har soatda avtomatik (Task Scheduler)
```powershell
$script  = "C:\print-hisob\ad-sync\Sync-AdEmployees.ps1"    # o'z yo'lingizga moslang

$action  = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName "PrinterHisob-AdSync" `
    -Action $action -Trigger $trigger -Principal $principal `
    -Description "AD xodimlarini Printer Hisob API'ga har soatda sinxronlash"
```
> `SYSTEM` AD'ni o'qiy olmasa, domen foydalanuvchisi bilan ishga tushiring:
> `New-ScheduledTaskPrincipal -UserId "MADANIYAT\svc_adsync" -LogonType Password`

Sinov:
```powershell
Start-ScheduledTask -TaskName "PrinterHisob-AdSync"
Get-Content .\ad-sync.log -Tail 20
```

## Loglar
Skript yonida `ad-sync.log` — har ishga tushish, xodimlar soni va xatolar yoziladi.

## Muammolar
| Muammo | Yechim |
|---|---|
| `ActiveDirectory moduli yo'q` | RSAT o'rnating (yuqoriga qarang) |
| `401 Unauthorized` | `config.json` dagi `ApiKey` serverdagi `API_KEY` bilan mos emas |
| `To'xtatildi: faqat N ta xodim` | `SearchBase` yoki AD ulanishini tekshiring (himoya ishladi) |
| Dashboardда xodim "noma'lum" | `login` (sAMAccountName) print job'dagi `user` bilan mos emas |
| `department` bo'sh | `-Preview` bilan xom atributlarni ko'ring, manbani o'zgartiring |
