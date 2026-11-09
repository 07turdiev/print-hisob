r"""Foydalanuvchi loginlarini solishtirish uchun normallashtirish.

Agent hujjatidagi qoida (`/print-quotas`, "Uch nozik qoida", 3-band): foydalanuvchi
nomlari **registrga sezgir emas** va `DOMAIN\` prefiksi olib tashlangan holda
solishtiriladi — `ACME\Jane`, `jane`, `Jane` bitta odam hisoblanadi.

Bu qoida faqat kvota almashinuviga emas, umuman login solishtirishga tegishli:
`print_jobs.user_name` (agent hodisa jurnalidan olgan xom qiymat) va
`employees.login` (AD sinxronizatsiyasidan kelgan qiymat) har doim shu
funksiya orqali bir shaklga keltirilib solishtiriladi. SQL so'rovlarda buning
o'rniga `login_key` ishlatiladi.
"""

from sqlalchemy import func


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


# `^.*\` — oxirgi teskari chiziqqa qadar bo'lgan hamma narsa.
_SQL_DOMAIN_PREFIX_PATTERN = r"^.*\\"


def login_key(column):
    """SQL tomonda `normalize_login` bilan bir xil natija beradigan ifoda."""
    return func.lower(func.regexp_replace(column, _SQL_DOMAIN_PREFIX_PATTERN, ""))
