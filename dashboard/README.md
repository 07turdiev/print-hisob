# Printer Hisob — dashboard

Vue 3 + TypeScript + Vite asosidagi boshqaruv paneli. Backend: `../api` (FastAPI).

## Ishga tushirish

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # vue-tsc tekshiruvi + ishlab chiqarish uchun yig'ish
```

`.env` faylida `VITE_API_BASE_URL` ko'rsatiladi (namuna: `.env.example`).
Dashboard foydalanuvchilari JWT bilan kiradi (`POST /api/auth/login`).

## Dizayn tizimi

Ko'rinish O'zbekiston davlat axborot tizimlari (edo.ijro.uz) uslubida:
rasmiy ko'k rang, zich va chegaralangan jadvallar, tekis yuzalar, kichik radiuslar.

Barcha ranglar, o'lchovlar va umumiy sinflar **`src/style.css`** da — komponentlar
o'z ichida faqat joylashuvni yozadi, rangni qattiq kodlamaydi.

### Karkas

| Element | Fayl | Vazifasi |
| --- | --- | --- |
| Ko'k yuqori lenta | `components/AppTopBar.vue` | Brend, sana, mavzu, foydalanuvchi menyusi |
| Guruhlangan yon menyu | `components/AppSidebar.vue` | Bo'limlar: Asosiy / Hisobotlar / Ma'lumotnomalar / Nazorat |
| Sahifa sarlavhasi | `components/PageHeader.vue` | Nonchalar (breadcrumb), sarlavha, izoh, davr tanlagichi |

Sahifa sarlavhasi va nonchalar `router/index.ts` dagi `meta` dan olinadi:
`title`, `section`, `description`, `showPeriodSelector`.

### Umumiy CSS sinflari (`style.css`)

- `.page` — sahifa konteyneri (kenglik, chekkalar, elementlar orasidagi masofa)
- `.panel` + `.panel__head` / `__title` / `__count` / `__actions` / `__body` / `__foot` — asosiy oq blok
- `.filter-bar` + `.field` + `.search-box` — jadval ustidagi filtr lentasi
- `.btn`, `.btn-primary`, `.btn-sm`, `.icon-btn` — tugmalar
- `.badge--success|warning|danger|muted|accent` — holat nishonlari
- `.alert--danger|warning|info|success` — xabar lentalari
- `.col-num`, `.num`, `.nowrap`, `.muted`, `.strong`, `.negative` — jadval yordamchi sinflari
- `tr.row-danger|row-warning|row-muted` — ajratib ko'rsatiladigan qatorlar
- `.empty-state`, `.loading-pill`, `.pager`, `.bar-track`/`.bar-fill`

### Qayta ishlatiladigan komponentlar

`StatTile` (KPI kartochkasi), `KpiCards`, `EmployeeQuotaTable`, `UsageBar`,
`StatusBadge`, `TopList`, `FailuresPanel`, `TimeseriesChart`, `NamedBarChart`,
`AdSyncBanner`, `DepartmentFilter`, `CsvDownloadButton`, `AppIcon`.

Diagrammalar ranglari `utils/chartTheme.ts` da; qiymatlar jonli CSS o'zgaruvchilaridan
o'qiladi, shuning uchun mavzu almashganda diagramma ham o'zgaradi.

### Mavzu (light/dark)

`data-theme` atributi `<html>` ga qo'yiladi: `index.html` dagi kichik skript uni
Vue yuklanishidan oldin tiklaydi, keyin `composables/useTheme.ts` boshqaradi
(`localStorage` kaliti: `printerhisob.theme`).

## Konventsiyalar

- Kod izohlari va UI matni — o'zbekcha; identifikatorlar — inglizcha.
- Yangi rang kerak bo'lsa avval `style.css` ga token qo'shiladi, komponentga emas.
- Jadvallarda birinchi ustun — `T/r` (`.col-num`), sonlar — `.num` (o'ngga tekislangan).
