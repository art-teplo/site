import { cacheLife, cacheTag } from "next/cache";
import { brands, categories, demoCards, demoSeries, demoSeriesBySlug } from "./catalog";
import { demoShowcases, demoVariants } from "@/data/catalog-demo";
import { mapCard, mapVariants, mapShowcase, type ApiCard, type ApiShowcase, type ApiVariants } from "./catalog-map";
import { serializeCatalogQuery, type CatalogQuery, type Sort } from "@/lib/catalog-query";
import { faq, LEAD_TIMES_UPDATED, posts, projects, promos, showroomHall } from "./content";
import { demoSite } from "./site";
import type {
  Brand,
  CatalogField,
  Category,
  CategoryType,
  ColorGroup,
  Execution,
  Facet,
  Faq,
  ImageAsset,
  LeadTime,
  ModelTile,
  Post,
  PostCard,
  Project,
  Promo,
  SeriesDetail,
  SeriesImage,
  ShowcaseCard,
  Site,
  VariantRow,
} from "./types";

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
type ApiProject = Omit<Project, "series" | "videoUrl"> & { series_slugs: string[]; video_url?: string };
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
  return data.map(({ series_slugs, video_url, ...project }) => ({ ...project, videoUrl: video_url, series: series_slugs }));
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

type ApiCategoryType = Omit<CategoryType, "seriesCount"> & { series_count?: number; seriesCount?: number };
type ApiCategory = Omit<Category, "seriesCount" | "types"> & { series_count: number; types?: ApiCategoryType[] };
type ApiBrand = Omit<Brand, "warrantyYears" | "logo" | "seriesCount"> & {
  logo: Brand["logo"] | null;
  warranty_years: number | null;
  series_count: number;
};
type ApiLeadTime = LeadTime & { updated_at: string };

export async function getCategories(): Promise<Category[]> {
  const data = await load<ApiCategory[]>("categories/", "catalog");
  if (!data) return categories.map((c) => ({ ...c, seriesCount: demoSeries.filter((s) => s.category === c.slug).length }));
  return data.map(({ series_count, types, ...category }) => ({
    ...category,
    seriesCount: series_count,
    types: (types ?? []).map(({ series_count: n, seriesCount, ...t }) => ({ ...t, seriesCount: seriesCount ?? n ?? 0 })),
  }));
}

export async function getBrands(): Promise<Brand[]> {
  const data = await load<ApiBrand[]>("brands/", "catalog");
  if (!data) return brands.map((b) => ({ ...b, seriesCount: demoSeries.filter((s) => s.brand.slug === b.slug).length }));
  return data.map(({ warranty_years, logo, series_count, ...brand }) => ({
    ...brand,
    logo: logo ?? undefined,
    warrantyYears: warranty_years,
    seriesCount: series_count,
  }));
}

const DEMO_LEAD_DAYS: Record<string, number> = { "nova-siluet": 30, "guardo-retta-3p": 15, "guardo-stretto": 15 }; // демо: остальные — «уточнит менеджер»

// Таблица сроков и дата последней правки — она подписана под таблицей
export async function getLeadTimes(): Promise<{ rows: LeadTime[]; updated: string }> {
  const data = await load<ApiLeadTime[]>("lead-times/", "catalog");
  if (!data) {
    const rows = demoSeries.map((s) => ({ series: s.name, brand: s.brand.slug, days: DEMO_LEAD_DAYS[s.slug] ?? null }));
    return { rows, updated: LEAD_TIMES_UPDATED };
  }
  const updated = data.reduce((last, row) => (row.updated_at > last ? row.updated_at : last), "");
  const rows = data.map(({ series, brand, days }) => ({ series, brand, days }));
  return { rows, updated: updated.slice(0, 10) };
}

// --- Серии и варианты (пути плоские: /api/series/…, /api/variants/…) ---

type ApiField = Pick<CatalogField, "key" | "label" | "kind" | "unit">;
type ApiGroup = Omit<ColorGroup, "isBase" | "anyRal"> & { is_base: boolean; any_ral: boolean };
type ApiSeries = Omit<
  SeriesDetail,
  "pressureBar" | "warrantyYears" | "videoUrl" | "colorGroups" | "defaultExecution" | "columns" | "filters" | "images" | "executions" | "priceFrom" | "priceFromByGroup" | "similar" | "projects"
> & {
  similar?: ApiCard[];
  projects?: (Omit<Project, "series" | "videoUrl"> & { series_slugs?: string[]; series?: string[]; video_url?: string })[];
  price_from: number | null;
  price_from_by_group: Record<string, number | null>;
  pressure_bar: number | null;
  warranty_years: number | null;
  video_url: string;
  images: SeriesImage[];
  color_groups: ApiGroup[];
  executions: (Omit<Execution, "connection"> & { connection: Execution["connection"] | "" })[];
  default_execution: string | null;
  columns: ApiField[];
  filters: ApiField[];
};


// Витрина категории: карточки (серия в одном формфакторе), фильтры и модельный ряд выбранных брендов
export async function getShowcases(
  category: string,
  query: CatalogQuery,
): Promise<{ count: number; results: ShowcaseCard[]; facets: Facet[]; modelRange: ModelTile[] }> {
  const params = `category=${encodeURIComponent(category)}&${serializeCatalogQuery({ ...query, v: undefined })}`;
  const data = await load<ApiShowcase>(
    `series/?${params}`,
    "catalog",
  );
  if (!data) return demoShowcases(category, query);
  return mapShowcase(data);
}

export async function getSeries(slug: string): Promise<SeriesDetail | null> {
  const data = await load<ApiSeries>(`series/${encodeURIComponent(slug)}/`, "catalog");
  if (data === undefined) return demoSeriesBySlug(slug) ?? null;
  if (data === null) return null;
  const { pressure_bar, warranty_years, video_url, color_groups, default_execution, columns, filters, executions, price_from, price_from_by_group, similar, projects: seriesProjects, ...rest } = data;
  return {
    ...rest,
    priceFrom: price_from,
    priceFromByGroup: Object.fromEntries(Object.entries(price_from_by_group).map(([id, price]) => [Number(id), price])),
    pressureBar: pressure_bar,
    warrantyYears: warranty_years,
    videoUrl: video_url,
    colorGroups: color_groups.map(({ is_base, any_ral, ...group }) => ({ ...group, isBase: is_base, anyRal: any_ral })),
    // без подключения бэк отдаёт '' — на фронте это null
    executions: executions.map((e) => ({ ...e, connection: e.connection || null })),
    defaultExecution: default_execution,
    columns: columns.map((c) => ({ ...c, column: true, filter: false })),
    filters: filters.map((c) => ({ ...c, column: false, filter: true })),
    similar: similar ? mapShowcase({ count: similar.length, results: similar, facets: [], model_range: [] }).results : [],
    projects: (seriesProjects ?? []).map(({ series_slugs, series, video_url, ...project }) => ({ ...project, videoUrl: video_url, series: series_slugs ?? series ?? [] })),
  };
}

// Строки таблицы серии. Бренд и v в бэк не уходят: бренд серии известен, v — только для адреса страницы
export async function getVariants(
  slug: string,
  query: CatalogQuery,
): Promise<{ count: number; results: VariantRow[]; facets: Facet[] }> {
  const params = serializeCatalogQuery({ ...query, brand: undefined, v: undefined });
  const data = await load<ApiVariants>(`series/${encodeURIComponent(slug)}/variants/?${params}`, "catalog");
  if (!data) return demoVariants(slug, query);
  return mapVariants(data);
}

// Поиск по сайту: до 20 карточек витрины. Без бэка — по названию и бренду демо-серий
// Поиск: слова, раскладка и синонимы разбирает бэк (apps/catalog/search.py). sort — как в каталоге
export async function getSearch(q: string, sort?: Sort): Promise<ShowcaseCard[]> {
  const query = q.trim();
  if (query.length < 2) return [];
  const params = new URLSearchParams({ q: query });
  if (sort) params.set("sort", sort);
  const data = await load<ApiCard[]>(`search/?${params}`, "catalog");
  if (!data) {
    const needle = query.toLowerCase();
    const found = categories
      .flatMap((c) => demoCards(c.slug).map((card) => ({ ...card, category: c.slug })))
      .filter((card) => `${card.name} ${card.brand}`.toLowerCase().includes(needle))
      .slice(0, 20);
    const sign = sort === "-price" ? -1 : 1;
    return sort ? found.sort((a, b) => sign * ((a.priceFrom ?? Infinity) - (b.priceFrom ?? Infinity))) : found;
  }
  return data.map(mapCard);
}

// Категория серии по слагу: у проектов есть только слаги серий, а адрес серии — /catalog/<категория>/<серия>
export async function getSeriesCategories(slugs: string[]): Promise<Record<string, { category: string; name: string }>> {
  const found = await Promise.all([...new Set(slugs)].map(async (slug) => [slug, await getSeries(slug).catch(() => null)] as const));
  return Object.fromEntries(found.flatMap(([slug, s]) => (s ? [[slug, { category: s.category, name: s.name }]] : [])));
}
