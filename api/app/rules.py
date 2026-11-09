"""Hisobot raqamlarini belgilaydigan qoidalar. Barchasi: `docs/QOIDALAR.uz.md`.

Har bir hisobot shu yerdagi shartlardan foydalanadi, shuning uchun bir sahifadagi
raqam boshqasidan farq qilmaydi.
"""

from sqlalchemy import and_, func, not_, or_

from app.models import PrintJob

# Qog'oz sarflamaydigan (faylga yoki ilovaga yozadigan) printerlar nomi.
VIRTUAL_PRINTER_PATTERN = r"pdf|xps|onenote|evernote|fax|[фФ]акс"
_IPV4_PATTERN = r"^\d+\.\d+\.\d+\.\d+$"

# Agent yuboradigan bekor qilish sabablari. "Canceled by" ostiga kvota va printer
# siyosati kiradi, "Print job was canceled" esa spooler yoki foydalanuvchi bekor qilgani.
_CANCELLED_REASON_PATTERN = r"^(Print job was canceled|Canceled by )"


def paper_job():
    """Qog'ozga chiqadigan printerga yuborilgan ish.

    Agent virtual printerlarning (Microsoft Print to PDF va boshqalar) sahifalarini
    ham `pages` qilib yuboradi, ular esa qog'oz sarflamaydi. Faqat nomga qaralmaydi:
    MAC yoki IP bilan kelgan yozuv tarmoqdagi haqiqiy printerga tegishli, nomida
    "pdf" so'zi bo'lsa ham.
    """
    return not_(
        and_(
            PrintJob.printer.op("~*")(VIRTUAL_PRINTER_PATTERN),
            PrintJob.printer_mac.is_(None),
            or_(PrintJob.printer_ip.is_(None), PrintJob.printer_ip.op("!~")(_IPV4_PATTERN)),
        )
    )


def cancelled_job():
    """Printerga yetmagan, bekor qilingan ish: qog'oz sarflanmagan va bu xato emas.

    Agent bitta chop etishni ko'pincha ikki yozuv qilib yuboradi: biri
    muvaffaqiyatli, biri "canceled". 4-chorakda 3 186 ta shunday yozuvning 98
    foizida ayni hujjat baribir chiqqan.
    """
    return and_(
        PrintJob.success.is_(False),
        PrintJob.pages == 0,
        func.coalesce(PrintJob.reason, "").op("~*")(_CANCELLED_REASON_PATTERN),
    )


def counted_job():
    """Sarf va ish soni hisobotlariga kiradigan yozuv.

    Jurnal, sabablar paneli va ruxsat hisoboti bu shartni qo'llamaydi: ular
    bekor qilingan va virtual printerga yuborilgan ishlarni ham ko'rsatadi.
    """
    return and_(paper_job(), not_(cancelled_job()))
