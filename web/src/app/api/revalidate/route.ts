import { timingSafeEqual } from "node:crypto";
import { revalidateTag } from "next/cache";

// Бэк зовёт после правки контента в админке (apps/content/tasks.py): обновить страницы с тегами.
// На сервере nginx отдаёт /api/ бэку, поэтому снаружи этот адрес недоступен — Celery ходит на web:3000.
const SECRET = process.env.REVALIDATE_SECRET ?? "";
const TAGS = new Set(["site", "faq", "projects", "posts", "showroom"]);

function authorized(header: string | null) {
  const expected = Buffer.from(`Bearer ${SECRET}`);
  const given = Buffer.from(header ?? "");
  return SECRET !== "" && given.length === expected.length && timingSafeEqual(given, expected);
}

export async function POST(request: Request) {
  if (!authorized(request.headers.get("authorization"))) {
    return Response.json({ ok: false }, { status: 401 });
  }
  const body: { tags?: unknown } = await request.json().catch(() => ({}));
  const tags = Array.isArray(body.tags) ? body.tags.filter((tag) => TAGS.has(tag)) : [];
  for (const tag of tags) revalidateTag(tag, { expire: 0 }); // правку видно с первого же захода
  return Response.json({ ok: true, tags });
}
