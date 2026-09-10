<#
.SYNOPSIS
    Prod serverdagi holatni tekshiradi (faqat o'qish).

.DESCRIPTION
    Dashboard login/parolini so'raydi, JWT token oladi va bir necha savolga
    javob beradi:
      - Printerlarning MAC manzillari kelayaptimi?
      - Chop etish kvota tufayli bekor qilinayaptimi?
      - Agentlar qaysi versiyada va nechtasi aloqada?
      - AD sinxronizatsiyasi qanday holatda?

    Hech narsa o'zgartirilmaydi — faqat GET so'rovlar.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Check-Prod.ps1
#>

param(
    [string]$BaseUrl = "https://print.madaniyhayot.uz"
)

$ErrorActionPreference = "Stop"

function Get-Json {
    param([string]$Url, [hashtable]$Headers)
    $r = Invoke-WebRequest -Uri $Url -Headers $Headers -UseBasicParsing -TimeoutSec 30
    # PowerShell 5.1 UTF-8 ni buzmasligi uchun xom baytlardan o'qiymiz
    $text = [System.Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray())
    return @{ Data = ($text | ConvertFrom-Json); Headers = $r.Headers }
}

Write-Host "=== Printer Hisob — prod tekshiruvi ===" -ForegroundColor Cyan
Write-Host "Server: $BaseUrl`n"

$user = Read-Host "Dashboard foydalanuvchi nomi"
$secure = Read-Host "Parol" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))

$body = @{ username = $user; password = $plain } | ConvertTo-Json
try {
    $login = Invoke-WebRequest -Uri "$BaseUrl/api/auth/login" -Method POST -Body $body `
        -ContentType 'application/json' -UseBasicParsing -TimeoutSec 30
} catch {
    Write-Host "Kirish muvaffaqiyatsiz: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
$token = ($login.Content | ConvertFrom-Json).accessToken
$h = @{ Authorization = "Bearer $token" }
Write-Host "Kirish muvaffaqiyatli.`n" -ForegroundColor Green

$now = Get-Date
$q = [math]::Ceiling($now.Month / 3)
$periodQ = "period_type=quarter&year=$($now.Year)&period_no=$q"

# --- 1. Umumiy ko'rsatkichlar --------------------------------------------
Write-Host "--- 1. Joriy chorak ($($now.Year), $q-chorak) ---" -ForegroundColor Yellow
$s = (Get-Json "$BaseUrl/api/stats/summary?$periodQ" $h).Data
"  Varaqlar: $($s.totalPages)   Buyurtmalar: $($s.totalJobs)   Printerlar: $($s.activePrinters)   Standart kvota: $($s.defaultQuota)"

# --- 2. Printer MAC qamrovi ----------------------------------------------
Write-Host "`n--- 2. Printerlar (MAC bo'yicha ajratish ishlayaptimi) ---" -ForegroundColor Yellow
$stats = (Get-Json "$BaseUrl/api/stats/printers?$periodQ" $h).Data
$withMac = @($stats | Where-Object { $_.mac })
$noMac = @($stats | Where-Object { -not $_.mac })
"  Davrda ishlatilgan printerlar : $(@($stats).Count)"
"  MAC bilan aniqlangan          : $($withMac.Count)"
"  MAC yo'q (nom bo'yicha)       : $($noMac.Count)"

$registry = (Get-Json "$BaseUrl/api/printers" $h).Data
"  Reyestrdagi printerlar        : $(@($registry).Count)"
$named = @($registry | Where-Object { $_.name })
"  Qo'lda nom berilganlari       : $($named.Count)"
if (@($registry).Count -gt 0) {
    Write-Host "`n  Reyestr (birinchi 15 ta):"
    $registry | Select-Object -First 15 mac, name, displayName, lastIp, lastSeen |
        Format-Table -AutoSize | Out-String | Write-Host
}

# --- 3. Kvota gipotezasi --------------------------------------------------
Write-Host "--- 3. Xatoliklar sababi (kvota tufayli bekor qilinyaptimi?) ---" -ForegroundColor Yellow
$fails = (Get-Json "$BaseUrl/api/stats/failures?$periodQ" $h).Data
if (@($fails).Count -eq 0) {
    "  Bu davrda xatolik qayd etilmagan."
} else {
    $fails | Select-Object reason, count | Format-Table -AutoSize | Out-String | Write-Host
    $quota = @($fails | Where-Object { $_.reason -match 'quota|кvota|kvota' })
    if ($quota.Count -gt 0) {
        Write-Host "  >>> KVOTA TUFAYLI BEKOR QILINGAN ISHLAR TOPILDI <<<" -ForegroundColor Red
        $quota | ForEach-Object { "      $($_.count) ta : $($_.reason)" }
    } else {
        Write-Host "  Kvota bilan bog'liq bekor qilish topilmadi." -ForegroundColor Green
    }
}

# --- 4. Agentlar ----------------------------------------------------------
Write-Host "`n--- 4. Agentlar ---" -ForegroundColor Yellow
$sum = (Get-Json "$BaseUrl/api/agents/summary" $h).Data
"  Jami: $($sum.total)   Ishlayapti: $($sum.working)   Xato: $($sum.notWorking)   Aloqa yo'q: $($sum.stale)   Qayta ishga tushgan: $($sum.recentlyRestarted)"
$agents = (Get-Json "$BaseUrl/api/agents" $h).Data
if (@($agents).Count -gt 0) {
    Write-Host "`n  Versiyalar bo'yicha:"
    $agents | Group-Object version | Sort-Object Count -Descending |
        Select-Object @{n='Versiya';e={$_.Name}}, Count |
        Format-Table -AutoSize | Out-String | Write-Host
}

# --- 5. AD sinxronizatsiyasi ---------------------------------------------
Write-Host "--- 5. AD sinxronizatsiyasi ---" -ForegroundColor Yellow
$ad = (Get-Json "$BaseUrl/api/ad-sync/status" $h).Data
"  Xodimlar: $($ad.employeeCount)   Faol: $($ad.activeCount)   Oxirgi sinxron: $($ad.minutesSinceSync) daqiqa oldin   Eskirgan: $($ad.isStale)"

# --- 6. AD mosligi --------------------------------------------------------
Write-Host "`n--- 6. Loginlar AD bilan mos keladimi ---" -ForegroundColor Yellow
$emps = (Get-Json "$BaseUrl/api/stats/employees?$periodQ" $h).Data
$unmatched = @($emps | Where-Object { $_.matchStatus -eq 'unmatched' })
$inactive = @($emps | Where-Object { $_.matchStatus -eq 'inactive' })
"  Chop etgan loginlar : $(@($emps).Count)"
"  AD'da topilmadi     : $($unmatched.Count)"
"  Ketgan xodimlar     : $($inactive.Count)"
if ($unmatched.Count -gt 0) {
    Write-Host "`n  Topilmagan loginlar:"
    $unmatched | Select-Object login, used | Format-Table -AutoSize | Out-String | Write-Host
}

# --- 7. Limitdan oshganlar -----------------------------------------------
$over = @($emps | Where-Object { $_.overLimit })
Write-Host "--- 7. Limitdan oshgan xodimlar: $($over.Count) ta ---" -ForegroundColor Yellow
if ($over.Count -gt 0) {
    $over | Select-Object -First 20 login, fullName, used, allocated |
        Format-Table -AutoSize | Out-String | Write-Host
}

Write-Host "=== Tekshiruv tugadi ===" -ForegroundColor Cyan
