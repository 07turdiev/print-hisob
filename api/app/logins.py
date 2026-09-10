r"""Foydalanuvchi loginlarini solishtirish uchun normallashtirish.

Agent hujjatidagi qoida (`/print-quotas`, "Uch nozik qoida", 3-band): foydalanuvchi
nomlari **registrga sezgir emas** va `DOMAIN\` prefiksi olib tashlangan holda
solishtiriladi — `ACME\Jane`, `jane`, `Jane` bitta odam hisoblanadi.

Bu qoida faqat kvota almashinuviga emas, umuman login solishtirishga tegishli:
`print_jobs.user_name` (agent hodisa jurnalidan olgan xom qiymat) va
`employees.login` (AD sinxronizatsiyasidan kelgan qiymat) har doim shu
funksiya orqali bir shaklga keltirilib solishtiriladi.
"""


def normalize_login(raw: str | None) -> str:
    r"""`MADANIYAT\E.Turdiyev` -> `e.turdiyev`.

    Domen prefiksi (oxirgi `\` gacha bo'lgan qism) olib tashlanadi va natija
    kichik harfga o'tkaziladi. Bo'sh yoki `None` qiymat uchun bo'sh satr qaytadi.
    """
    if not raw:
        return ""
    value = raw.strip()
    if "\\" in value:
        value = value.rsplit("\\", 1)[-1]
    return value.casefold()


# SQL tomonda xuddi shu normallashtirishni bajaradigan ifoda uchun regex:
# `^.*\` — oxirgi teskari chiziqqa qadar bo'lgan hamma narsa.
SQL_DOMAIN_PREFIX_PATTERN = r"^.*\\"
