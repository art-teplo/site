# art-teplo.by — фронтенд

Next.js 16 (App Router, TypeScript, Cache Components), CSS Modules + CSS-переменные, Lenis.
Бриф и решения: [`../docs/brief.md`](../docs/brief.md), [`../docs/decisions.md`](../docs/decisions.md), фото — [`../docs/images-manifest.md`](../docs/images-manifest.md).

```bash
npm install
npm run dev      # http://localhost:3000
npm run build && npm start
npm run lint
```

## Структура

```
src/
  styles/
    tokens.css     ← все цвета, размеры, радиусы, тени, движение. Единственное место со «значениями»
    base.css       ← сброс, базовая типографика, утилиты (.visually-hidden, .skip-link)
  components/      ← маленькие переиспользуемые блоки, по папке на компонент: Name/Name.tsx + Name.module.css
  sections/        ← секции страниц, собранные из компонентов (home/, catalog/, product/, page/ — блоки внутренних страниц)
  app/             ← страницы (роуты Next): /, /catalog, /catalog/[category], /catalog/[category]/[product],
                     /podbor, /uslugi, /proekty, /shourum, /klientam, /partneram, /blog, /kontakty, /brendy, /privacy
  data/            ← данные отдельно от разметки; форма повторяет будущий API Django/DRF
  lib/             ← чистые функции: форматирование, фильтры каталога, текущий год
public/images/     ← изображения; сейчас плейсхолдеры, реальные фото кладутся по тем же путям
```

Слои зависят только «вниз»: `app → sections → components → styles`. Компонент не импортирует секцию, секция не импортирует страницу.

## Правила

1. **Только токены.** В `*.module.css` нет hex/rgb и «магических» px — только `var(--…)` из `tokens.css`. Полупрозрачные варианты — `color-mix(in srgb, var(--color-…) N%, transparent)`. Исключения: 1px-линии, брейкпоинты в `@media` (там переменные не работают: мобильный ≤ 767, планшет 768–1023, десктоп ≥ 1024).
2. **Тон секции, а не цвет.** Светлая/тёмная/белая поверхность задаётся `<Section tone="dark">` (атрибут `data-tone`); компоненты берут `--text`, `--text-muted`, `--bg`, `--surface`, `--line`, `--button-bg/fg` и сами перекрашиваются.
3. **Один язык движения.** Заголовки — `<SplitText>` внутри `<Reveal effect="mask">` (слова из-под маски); блоки — `<Reveal index={i}>` (fade + сдвиг, stagger). Метки и номера над заголовками не ставим. Длительности и кривые — `--dur-*`, `--ease-*`. Анимируются только `transform` и `opacity`. `prefers-reduced-motion` обнуляет токены движения и выключает Lenis.
4. **Интерактив.** У всего кликабельного есть `:hover`, `:focus-visible` (глобальное красное кольцо из `base.css`) и `:active` (`scale(var(--press-scale))` или общий `opacity` для текстовых ссылок).
5. **Изображения** — только через `<Picture>` (`<picture>`, AVIF/WebP, width/height, lazy). Для первого экрана — `eager`. Новый слот — запись в `docs/images-manifest.md`. Заменили файлы в `public/images` — увеличьте `IMAGES_VERSION` в `lib/asset.ts`, иначе браузеры до 4 часов показывают старые.
6. **Типографика:** один шрифт Onest: заголовки `h1–h4` — 500 с плотным трекингом (из `base.css`), текст — 400. Размеры — `--text-*`.
7. **Cache Components:** `new Date()` в серверных компонентах нельзя — используйте `currentYear()` из `lib/year.ts` (`"use cache"`). `useSearchParams` — только внутри `<Suspense>`.

## Как добавить компонент

1. `src/components/Name/Name.tsx` + `Name.module.css`. Одна ответственность; props типизированы; комментарий одной строкой — зачем он.
2. Стили — только через токены (правило 1). Нужен новый размер/цвет — сначала добавьте токен в `tokens.css`.
3. Если нужен JS (состояние, события) — `"use client"` в этом файле, а не в секции целиком.
4. Состояния hover / focus-visible / active, проверка на 375 / 768 / 1440 и с `prefers-reduced-motion`.
5. `npm run lint && npm run build`.

## Что пока заглушка

- Отправка формы (`LeadForm`) имитируется — нужен `POST /api/leads/` на бэкенде.
- Данные каталога, проекты, FAQ и блог — демо (`src/data`).
- Виджет отзывов Яндекс.Карт, видео шоурума, страницы отдельных проектов. Тексты статей — черновик.
- Тексты внутренних страниц — черновик (`data/content.ts`), сверить с заказчиком.
