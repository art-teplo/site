# Фронтенд

Общие правила — в `../AGENTS.md`. Перед правками прочитай `README.md`: в нём структура, правила CSS, компонентов, анимаций, изображений и кэша. Дизайн — `../DESIGN.md`, продуктовые решения — `../docs/decisions.md`.

- Запуск и команды — в `README.md`; зависимости фиксирует `package-lock.json`, пакетный менеджер — npm.
- Данные и инвалидация кэша связаны с бэком: меняя API или теги, проверь обе стороны (`src/data/api.ts`, `src/app/api/revalidate/route.ts`, `../backend/src/apps/content/models.py`).
- Изменения поведения полей админки требуют обновить `../docs/admin-guide.md`; новые слоты фото — `../docs/images-manifest.md`.
- После правок кода: `npm run lint && npm run build`. После правок вёрстки дополнительно проверь 375, 768 и 1440 px и уменьшение движения, как описано в README.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
