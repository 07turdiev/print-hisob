<#
.SYNOPSIS
    Active Directory'dan xodimlarni o'qib, Printer Hisob API'ga (POST /api/ad-sync) yuboradi.

.DESCRIPTION
    Har soatda Task Scheduler orqali ishlaydi. AD'dan foydalanuvchilarni oladi va
    login / to'liq ism / bo'lim / lavozim / holat (faol-yo'q) ni backend'ga upsert qiladi.
    Backend idempotent: qayta yuborish xavfsiz.

    MAYDON MANBALARI sozlanadi (config.json), chunki har AD'da boshqacha to'ldirilgan:
      DepartmentSource : "OU"          -> xodim turgan OU nomi (masalan "Ichki audit bo'limi")
                         "Attribute"   -> AD `department` atributi
      PositionSource   : "Description" -> AD `description` atributi
                         "Title"       -> AD `title` atributi

    XAVFSIZLIK: `mode = "full"` da backend payloadda YO'Q xodimlarni is_active=false
    qiladi (ketgan deb belgilaydi). Shuning uchun AD so'rovi xato ketib bo'sh/juda kam
    natija qaytarsa, skript YUBORMAYDI va xato bilan to'xtaydi (MinEmployees tekshiruvi).

.PARAMETER Preview
    Hech narsa yubormaydi — AD'dan nima olinganini va qaysi maydonlar to'ldirilganini
    ko'rsatadi. BIRINCHI MARTA ALBATTA SHU BILAN ISHGA TUSHIRING.

.EXAMPLE
    .\Sync-AdEmployees.ps1 -Preview      # avval sinab ko'rish (hech narsa yuborilmaydi)
    .\Sync-AdEmployees.ps1               # haqiqiy sinxronizatsiya
#>

[CmdletBinding()]
param(
    [switch]$Preview,
    [string]$ConfigPath = (Join-Path $PSScriptRoot 'config.json')
)

$ErrorActionPreference = 'Stop'

$LogFile = Join-Path $PSScriptRoot 'ad-sync.log'

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = "{0} [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Get-OuFromDn {
    <#
      DN'dan xodimning eng yaqin OU'sini oladi (= uning bo'limi).
      Misol: "CN=Izzatullo Akbarov,OU=Ichki audit bo'limi,OU=Madaniyat vazirligi,DC=madaniyat,DC=local"
             -> "Ichki audit bo'limi"
      DN'da vergul `\,` bilan ekranlanadi (masalan "Madaniy faoliyat\, nomoddiy...") — buni hisobga olamiz.
    #>
    param([string]$Dn)
    if ($Dn -match ',OU=(?<ou>(?:[^,\\]|\\.)+)') {
        return ($Matches['ou'] -replace '\\(.)', '$1')
    }
    return ''
}

try {
    # -----------------------------------------------------------------------
    # 1. Konfiguratsiya
    # -----------------------------------------------------------------------
    if (-not (Test-Path $ConfigPath)) {
        throw "config.json topilmadi: $ConfigPath  (config.example.json dan nusxa oling)"
    }
    $cfg = Get-Content -Path $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json

    foreach ($required in @('ApiUrl', 'ApiKey', 'AdServer')) {
        if ([string]::IsNullOrWhiteSpace($cfg.$required)) {
            throw "config.json da '$required' to'ldirilmagan."
        }
    }

    $mode         = if ($cfg.Mode) { $cfg.Mode } else { 'full' }
    $minEmployees = if ($cfg.MinEmployees) { [int]$cfg.MinEmployees } else { 5 }
    $deptSource   = if ($cfg.DepartmentSource) { $cfg.DepartmentSource } else { 'OU' }
    $posSource    = if ($cfg.PositionSource)   { $cfg.PositionSource }   else { 'Description' }
    # AD'dagi Enabled bayrog'i bu tashkilotда ishonchli emas (ko'p akkaunt Disabled, lekin
    # xodimlar ishlayapti). Standart: AD'da MAVJUD = faol. Ketgan/kelgan aniqlash
    # `mode=full` snapshot farqi orqali bo'ladi (ro'yxatda yo'q -> backend is_active=false qiladi).
    $useAdEnabled = if ($null -ne $cfg.UseAdEnabledFlag) { [bool]$cfg.UseAdEnabledFlag } else { $false }

    Write-Log ("Boshlandi. AD=$($cfg.AdServer) mode=$mode dept=$deptSource pos=$posSource " +
               "useAdEnabled=$useAdEnabled preview=$Preview")

    # -----------------------------------------------------------------------
    # 2. ActiveDirectory moduli
    # -----------------------------------------------------------------------
    if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
        throw ("ActiveDirectory moduli yo'q. RSAT o'rnating: " +
               "Add-WindowsCapability -Online -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0")
    }
    Import-Module ActiveDirectory -ErrorAction Stop

    # -----------------------------------------------------------------------
    # 3. AD'dan foydalanuvchilarni olish
    # -----------------------------------------------------------------------
    $adParams = @{
        Server     = $cfg.AdServer
        Filter     = '*'
        Properties = @('DisplayName', 'Department', 'Title', 'Description',
                       'Enabled', 'SamAccountName', 'DistinguishedName')
    }
    # SearchBase — faqat xodimlar turgan OU (Builtin/Computers va h.k. tushmasligi uchun).
    if (-not [string]::IsNullOrWhiteSpace($cfg.SearchBase)) {
        $adParams['SearchBase'] = $cfg.SearchBase
    }

    $users = Get-ADUser @adParams
    Write-Log "AD'dan olindi: $(@($users).Count) ta foydalanuvchi"

    # -----------------------------------------------------------------------
    # 4. Kerakli maydonlarga o'girish
    # -----------------------------------------------------------------------
    # Bo'sh satrlar backend'da NULL bo'ladi — bemalol "" yuborsa bo'ladi.
    $employees = @(
        foreach ($u in $users) {
            if ([string]::IsNullOrWhiteSpace($u.SamAccountName)) { continue }
            if ($cfg.ExcludeLogins -and ($cfg.ExcludeLogins -contains $u.SamAccountName)) { continue }

            $fullName = if (-not [string]::IsNullOrWhiteSpace($u.DisplayName)) { $u.DisplayName }
                        else { $u.Name }

            $department = if ($deptSource -eq 'Attribute') { [string]$u.Department }
                          else { Get-OuFromDn $u.DistinguishedName }

            $position = if ($posSource -eq 'Title') { [string]$u.Title }
                        else { [string]$u.Description }

            # AD'da mavjud bo'lsa — faol. (Ketganlar AD'dan o'chiriladi va `mode=full`
            # snapshot'ida bo'lmaydi -> backend ularni is_active=false qiladi.)
            $isActive = if ($useAdEnabled) { [bool]$u.Enabled } else { $true }

            [pscustomobject]@{
                login      = [string]$u.SamAccountName
                fullName   = [string]$fullName
                department = [string]$department
                position   = [string]$position
                active     = $isActive
            }
        }
    )

    $total   = @($employees).Count
    $activeN = @($employees | Where-Object { $_.active }).Count
    $noDept  = @($employees | Where-Object { [string]::IsNullOrWhiteSpace($_.department) }).Count
    $noPos   = @($employees | Where-Object { [string]::IsNullOrWhiteSpace($_.position) }).Count
    Write-Log "Tayyor: $total xodim (faol: $activeN, bo'limsiz: $noDept, lavozimsiz: $noPos)"

    # -----------------------------------------------------------------------
    # 5. XAVFSIZLIK: bo'sh/kam ro'yxatni 'full' rejimda yubormaymiz
    # -----------------------------------------------------------------------
    if ($mode -eq 'full' -and $total -lt $minEmployees) {
        throw ("To'xtatildi: faqat $total ta xodim topildi (minimum $minEmployees). " +
               "'full' rejimda bu HAMMA xodimni 'ketgan' deb belgilagan bo'lardi. " +
               "SearchBase yoki AD ulanishini tekshiring.")
    }

    # -----------------------------------------------------------------------
    # 6. Preview — yubormasdan ko'rsatish
    # -----------------------------------------------------------------------
    if ($Preview) {
        Write-Log 'PREVIEW — hech narsa yuborilmadi.'

        Write-Host "`n--- Yuboriladigan ko'rinish (birinchi 15) ---"
        $employees | Select-Object -First 15 | Format-Table -AutoSize | Out-String | Write-Host

        Write-Host "--- AD xom atributlari (qaysi maydon to'ldirilgan?) ---"
        $users | Select-Object -First 15 SamAccountName, DisplayName,
            @{N='OU';         E={ Get-OuFromDn $_.DistinguishedName }},
            @{N='Department'; E={ $_.Department }},
            @{N='Title';      E={ $_.Title }},
            @{N='Description';E={ $_.Description }} |
            Format-Table -AutoSize | Out-String | Write-Host

        $depts = @($employees.department | Where-Object { $_ } | Sort-Object -Unique)
        Write-Log ("Topilgan bo'limlar ($($depts.Count) ta): " + ($depts -join ' | '))
        return
    }

    # -----------------------------------------------------------------------
    # 7. Backend'ga yuborish
    # -----------------------------------------------------------------------
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $payload = [ordered]@{
        mode      = $mode
        employees = @($employees)
    }
    $json = $payload | ConvertTo-Json -Depth 5
    # UTF-8 bayt sifatida yuboramiz — aks holda o'zbekcha harflar (o', g', ') buziladi.
    $body = [System.Text.Encoding]::UTF8.GetBytes($json)

    $response = Invoke-RestMethod -Uri $cfg.ApiUrl `
        -Method Post `
        -Headers @{ 'X-API-Key' = $cfg.ApiKey } `
        -ContentType 'application/json; charset=utf-8' `
        -Body $body `
        -TimeoutSec 120

    Write-Log ("Yuborildi. Javob: received={0} upserted={1} deactivated={2}" -f `
        $response.received, $response.upserted, $response.deactivated)
    Write-Log 'Muvaffaqiyatli yakunlandi.'
    exit 0
}
catch {
    Write-Log $_.Exception.Message 'ERROR'
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) { Write-Log $_.ErrorDetails.Message 'ERROR' }
    exit 1
}
