import { cacheLife, cacheTag } from "next/cache";
import { brands, categories, products } from "./catalog";
import { faq, LEAD_TIMES_UPDATED, posts, projects, promos, showroomHall } from "./content";
import { demoSite } from "./site";
import type { Brand, Category, Faq, ImageAsset, LeadTime, Post, PostCard, Project, Promo, Site } from "./types";

// Контент из админки (бэк: apps/content). Без API_URL — демо-данные из src/data, как на Vercel.
// Ответы кэшируются по тегам; после правки бэк зовёт /api/revalidate с тегом раздела.
// API_URL — адрес бэка для сервера Next: в Docker http://backend:8000, локально http://localhost:8000.
// Браузер в бэк напрямую не ходит: /api/ и /media/ на том же домене (nginx, а в разработке — rewrites).
const API_URL = process.env.API_URL;
// При сборке бэка нет (CI собирает образ без него): страницы собираются на демо, а при деплое
// deploy.sh сбрасывает все теги, и первый же заход берёт данные из админки
const BUILDING = process.env.NEXT_PHASE === "phase-production-build";

// Теги — те же, что models.Tag на бэке
type Tag = "site" | "faq" | "projects" | "posts" | "showroom" | "catalog";

// undefined — бэка нет (демо), null — бэк ответил 404
async function load<T>(path: string, tag: Tag): Promise<T | null | undefined> {
  "use cache";
  cacheTag(tag);
  cacheLife("hours"); // страховка, если бэк не достучался до /api/revalidate
  if (!API_URL || BUILDING) return undefined; // демо — тоже с тегом, чтобы его можно было сбросить
  // no-store: кэшем управляет только "use cache" с тегом. Иначе fetch ещё раз кладёт ответ в кэш Next
  // без тега — после правки в админке страница берёт старый ответ, а сборка переносит его в новую версию
  const response = await fetch(`${API_URL}/api/${path}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API ${path}: ${response.status}`);
  return response.json();
}

type ApiSite = {
  city: string;
  address: string;
  map_url: string;
  phone: string;
  phone_href: string;
  email: string;
  hours: { days: string; time: string }[];
  viber_url: string;
  telegram_url: string;
  instagram_url: string;
  instagram_handle: string;
  reply_promise: string;
  legal_name: string;
  unp: string;
  yandex_org_id: number | null;
  showroom_video: Site["showroomVideo"];
};
type ApiFaq = { question: string; answer: string; on_home: boolean };
type ApiProject = Omit<Project, "products"> & { product_slugs: string[] };
type ApiPostCard = Omit<PostCard, "date" | "readMinutes"> & { published_at: string; read_minutes: number };
type ApiPost = ApiPostCard & { body: string };

export async function getSite(): Promise<Site> {
  const data = await load<ApiSite>("site/", "site");
  if (!data) return demoSite;
  return {
    city: data.city,
    address: data.address,
    mapUrl: data.map_url,
    phone: data.phone,
    phoneHref: data.phone_href,
    email: data.email,
    hours: data.hours,
    viber: data.viber_url,
    telegram: data.telegram_url,
    instagram: data.instagram_url,
    instagramHandle: data.instagram_handle,
    replyPromise: data.reply_promise,
    // Пока заказчик не прислал реквизиты — видимая заглушка, как в демо
    legalName: data.legal_name || "[Уточнить у заказчика: юрлицо]",
    unp: data.unp || "[УНП]",
    yandexOrgId: data.yandex_org_id,
    showroomVideo: data.showroom_video,
  };
}

export async function getFaq(): Promise<Faq[]> {
  const data = await load<ApiFaq[]>("faq/", "faq");
  if (!data) return faq;
  return data.map((item) => ({ q: item.question, a: item.answer, onHome: item.on_home }));
}

export async function getProjects(): Promise<Project[]> {
  const data = await load<ApiProject[]>("projects/", "projects");
  if (!data) return projects;
  return data.map(({ product_slugs, ...project }) => ({ ...project, products: product_slugs }));
}

const toCard = ({ published_at, read_minutes, ...post }: ApiPostCard): PostCard => ({
  ...post,
  date: published_at,
  readMinutes: read_minutes,
});

export async function getPosts(): Promise<PostCard[]> {
  const data = await load<ApiPostCard[]>("posts/", "posts");
  if (!data) return posts;
  return data.map(toCard);
}

export async function getPost(slug: string): Promise<Post | null> {
  const data = await load<ApiPost>(`posts/${encodeURIComponent(slug)}/`, "posts");
  if (data === undefined) return posts.find((p) => p.slug === slug) ?? null;
  return data && { ...toCard(data), body: data.body };
}

// Тег — тот же, что у статей: акции живут на «Блог и акции». Закончившиеся бэк не отдаёт сам
export async function getPromos(): Promise<Promo[]> {
  const data = await load<(Omit<Promo, "endsAt"> & { ends_at: string | null })[]>("promos/", "posts");
  if (!data) return promos;
  return data.map(({ ends_at, ...promo }) => ({ ...promo, endsAt: ends_at }));
}

export async function getShowroom(): Promise<ImageAsset[]> {
  const data = await load<{ image: ImageAsset }[]>("showroom/", "showroom");
  if (!data) return showroomHall;
  return data.map((photo) => photo.image);
}

// --- Каталог (бэк: apps.catalog). Товары пока в коде и ссылаются на категории и бренды по slug ---

type ApiBrand = Omit<Brand, "warrantyYears" | "logo"> & { logo: Brand["logo"] | null; warranty_years: number | null };
type ApiLeadTime = LeadTime & { updated_at: string };

export async function getCategories(): Promise<Category[]> {
  const data = await load<Category[]>("categories/", "catalog");
  return data ?? categories;
}

export async function getBrands(): Promise<Brand[]> {
  const data = await load<ApiBrand[]>("brands/", "catalog");
  if (!data) return brands;
  return data.map(({ warranty_years, logo, ...brand }) => ({ ...brand, logo: logo ?? undefined, warrantyYears: warranty_years }));
}

// Таблица сроков и дата последней правки — она подписана под таблицей
export async function getLeadTimes(): Promise<{ rows: LeadTime[]; updated: string }> {
  const data = await load<ApiLeadTime[]>("lead-times/", "catalog");
  if (!data) {
    const rows = products.map((p) => ({ series: p.name, brand: p.brand, days: p.leadDays ?? null }));
    return { rows, updated: LEAD_TIMES_UPDATED };
  }
  const updated = data.reduce((last, row) => (row.updated_at > last ? row.updated_at : last), "");
  const rows = data.map(({ series, brand, days }) => ({ series, brand, days }));
  return { rows, updated: updated.slice(0, 10) };
}
