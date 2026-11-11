import { cacheLife, cacheTag } from "next/cache";
import { brands, categories, demoSeriesBySlug, demoSource, products, publicRow } from "./catalog";
import { demoShowcases, demoVariants } from "@/data/catalog-demo";
import { mapShowcase, type ApiShowcase } from "./catalog-map";
import { serializeCatalogQuery, type CatalogQuery } from "@/lib/catalog-query";
import { rowPrice } from "@/lib/price";
import { faq, LEAD_TIMES_UPDATED, posts, projects, promos, showroomHall } from "./content";
import { demoSite } from "./site";
import type {
  Brand,
  CatalogField,
  Category,
  ColorGroup,
  Connection,
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

// --- Серии и варианты (пути плоские: /api/series/…, /api/variants/…) ---

type ApiField = Pick<CatalogField, "key" | "label" | "kind" | "unit">;
type ApiRow = {
  article: string;
  height_mm: number | null;
  width_mm: number | null;
  depth_mm: number | null;
  length_mm: number | null;
  axis_mm: number | null;
  sections: number | null;
  power_w: number | null;
  area_m2: number | null;
  tubes: number | null;
  connection: Connection | "" | null;
  thermovalve: boolean;
  orientation: VariantRow["orientation"] | null;
  mount: VariantRow["mount"] | null;
  attrs: VariantRow["attrs"];
  price: number | null;
};
type ApiGroup = Omit<ColorGroup, "isBase" | "anyRal"> & { is_base: boolean; any_ral: boolean };
type ApiSeries = Omit<
  SeriesDetail,
  "pressureBar" | "warrantyYears" | "videoUrl" | "colorGroups" | "defaultExecution" | "columns" | "filters" | "images" | "executions"
> & {
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

const mapRow = (row: ApiRow): VariantRow => ({
  article: row.article,
  heightMm: row.height_mm,
  widthMm: row.width_mm,
  depthMm: row.depth_mm,
  lengthMm: row.length_mm,
  axisMm: row.axis_mm,
  sections: row.sections,
  powerW: row.power_w,
  areaM2: row.area_m2,
  tubes: row.tubes,
  connection: row.connection || null,
  thermovalve: row.thermovalve,
  orientation: row.orientation ?? "",
  mount: row.mount ?? "",
  attrs: row.attrs ?? {},
  price: row.price,
});

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
  const { pressure_bar, warranty_years, video_url, color_groups, default_execution, columns, filters, executions, ...rest } = data;
  return {
    ...rest,
    pressureBar: pressure_bar,
    warrantyYears: warranty_years,
    videoUrl: video_url,
    colorGroups: color_groups.map(({ is_base, any_ral, ...group }) => ({ ...group, isBase: is_base, anyRal: any_ral })),
    // без подключения бэк отдаёт '' — на фронте это null
    executions: executions.map((e) => ({ ...e, connection: e.connection || null })),
    defaultExecution: default_execution,
    columns: columns.map((c) => ({ ...c, column: true, filter: false })),
    filters: filters.map((c) => ({ ...c, column: false, filter: true })),
  };
}

// Строки таблицы серии. Бренд и v в бэк не уходят: бренд серии известен, v — только для адреса страницы
export async function getVariants(
  slug: string,
  query: CatalogQuery,
): Promise<{ count: number; results: VariantRow[]; facets: Facet[] }> {
  const params = serializeCatalogQuery({ ...query, brand: undefined, v: undefined });
  const data = await load<{ count: number; results: ApiRow[]; facets: Facet[] }>(
    `series/${encodeURIComponent(slug)}/variants/?${params}`,
    "catalog",
  );
  if (!data) return demoVariants(slug, query);
  return { count: data.count, results: data.results.map(mapRow), facets: data.facets };
}

// Один вариант с группами цветов, доступными ему. Один артикул в серии может быть дважды с разным
// подключением (повёрнутый радиатор) — тогда нужен connection из выбранного исполнения.
export async function getVariant(
  slug: string,
  article: string,
  connection?: Connection,
): Promise<(VariantRow & { availableGroups: number[] }) | null> {
  const params = `series=${encodeURIComponent(slug)}${connection ? `&connection=${connection}` : ""}`;
  const data = await load<ApiRow & { available_groups: number[] }>(`variants/${encodeURIComponent(article)}/?${params}`, "catalog");
  if (data === null) return null;
  if (data) return { ...mapRow(data), availableGroups: data.available_groups };
  const series = demoSeriesBySlug(slug);
  const source = demoSource(slug).find((r) => r.article === article && (!connection || r.connection === connection));
  if (!series || !source) return null;
  return {
    ...publicRow(source, rowPrice(source, series.colorGroups)),
    availableGroups: source.colorGroups.length ? source.colorGroups : series.colorGroups.map((g) => g.id),
  };
}
