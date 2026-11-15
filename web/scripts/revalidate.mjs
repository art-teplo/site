// Сбросить кэш фронта вручную: npm run revalidate [-- <порт или адрес> [теги…]]
//   npm run revalidate                 — все теги на http://localhost:3000
//   npm run revalidate -- 3010         — фронт на порту 3010
//   npm run revalidate -- 3000 catalog — только каталог
// Секрет — REVALIDATE_SECRET из web/.env.local (тот же, что BACKEND__FRONTEND__REVALIDATE_SECRET у бэка).
// Теги — как в src/app/api/revalidate/route.ts.

const ALL = ["site", "faq", "projects", "posts", "showroom", "catalog"];

const [target = "3000", ...picked] = process.argv.slice(2);
const base = /^\d+$/.test(target) ? `http://localhost:${target}` : target.replace(/\/$/, "");
const tags = picked.length ? picked : ALL;
const secret = process.env.REVALIDATE_SECRET;

if (!secret) {
  console.error("Нет REVALIDATE_SECRET в web/.env.local");
  process.exit(1);
}

try {
  const response = await fetch(`${base}/api/revalidate`, {
    method: "POST",
    headers: { authorization: `Bearer ${secret}`, "content-type": "application/json" },
    body: JSON.stringify({ tags }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    console.error(`${base}: ${response.status}${response.status === 401 ? " — секрет не совпадает с фронтом" : ""}`);
    process.exit(1);
  }
  console.log(`${base}: кэш сброшен (${(body.tags ?? tags).join(", ")})`);
} catch (error) {
  console.error(`${base}: фронт не отвечает — он запущен? (${error.cause?.code ?? error.message})`);
  process.exit(1);
}
