// Формы данных повторяют будущий API (Django + DRF). Когда появится бэкенд,
// файлы в src/data заменятся запросами, компоненты не изменятся.

export type ImageAsset = {
  src: string;
  width: number;
  height: number;
  alt: string;
};

export type CategorySlug = "radiatory" | "konvektory" | "polotentsesushiteli" | "armatura";

// Категории и бренды — из админки (apps.catalog); товары пока в коде и ссылаются на них по slug
export type Category = {
  slug: string;
  name: string;
  short: string;
  image: ImageAsset; // товар без фона, PNG с прозрачностью
  seriesCount: number; // опубликованные серии
};

export type Brand = {
  slug: string;
  name: string;
  country: string; // пусто — не показываем
  note: string;
  logo?: string; // с официальных сайтов производителей
  warrantyYears: number | null; // «гарантия до»; пусто — бренда нет в таблице гарантий
  seriesCount: number; // опубликованные серии
};

// Ориентир срока изготовления по серии — таблица на «Клиентам»
export type LeadTime = {
  series: string;
  brand: string; // Brand.slug
  days: number | null; // пусто — «уточнит менеджер»
};

export type Availability = "stock" | "order" | "request";

export type Variant = {
  id: string;
  heightMm: number;
  widthMm: number;
  sections?: number;
  powerW: number;
  priceByn: number;
};

export type ColorOption = {
  id: string;
  name: string;
  hex: string;
};

export type Product = {
  slug: string;
  name: string;
  brand: string; // Brand.slug
  category: CategorySlug;
  type: string;
  position?: "вертикальный" | "горизонтальный" | "напольный";
  material: string;
  heating: "водяной" | "электрический";
  connections: string[];
  colors: ColorOption[];
  variants: Variant[];
  depthMm: number;
  axisMm?: number;
  pressureBar: number;
  warrantyYears: number;
  availability: Availability;
  leadDays?: number;
  summary: string;
  images: ImageAsset[];
  videoUrl?: string;
  projects: string[]; // Project.slug
};

export type Project = {
  slug: string;
  title: string;
  kind: "квартира" | "дом" | "ЖК";
  place: string;
  image: ImageAsset;
  photos: ImageAsset[]; // ещё фото — листаются в галерее вместе с главным
  series: string[]; // Series.slug — связь необязательная
};

export type Faq = { q: string; a: string; onHome: boolean };

// Карточка статьи в списках; текст — только на странице статьи
export type PostCard = {
  slug: string;
  title: string;
  date: string;
  readMinutes: number;
  image: ImageAsset;
  lead: string;
};

// body — HTML из редактора админки, очищенный бэком (apps/content/html.py)
export type Post = PostCard & { body: string };

// Акция: своей страницы нет, весь текст — в карточке на /blog. endsAt — «действует до», null — бессрочная
export type Promo = { title: string; image: ImageAsset; body: string; endsAt: string | null };

// Контакты и реквизиты — «Настройки сайта» в админке
export type Site = {
  city: string;
  address: string;
  mapUrl: string;
  phone: string;
  phoneHref: string;
  email: string;
  hours: { days: string; time: string }[];
  viber: string;
  telegram: string;
  instagram: string;
  instagramHandle: string;
  legalName: string;
  unp: string;
  replyPromise: string;
  yandexOrgId: number | null; // карточка на Яндекс.Картах для виджета отзывов; null — только ссылка на карту
  showroomVideo: { src: string; poster: ImageAsset | null } | null; // файл из админки; нет — фото «скоро»
};

export type Service = {
  slug: string;
  title: string;
  text: string;
};

// --- Новый каталог: серии и варианты (бэк: apps.catalog, ответы /api/series/…) ---

export type Connection =
  | "side"
  | "diagonal"
  | "bottom_left"
  | "bottom_right"
  | "bottom_universal"
  | "bottom_ends"
  | "bottom_center"
  | "electric_left"
  | "electric_right";

export type ColorSwatch = { code: string; name: string; hex: string; finish?: string };

export type ColorGroup = {
  id: number;
  name: string;
  percent: number;
  isBase: boolean;
  anyRal: boolean;
  colors: ColorSwatch[];
};

export type CatalogField = {
  key: string;
  label: string;
  kind: "range" | "list" | "colors";
  unit: string;
  column: boolean;
  filter: boolean;
};

export type FacetValue = { value: string; label: string; count: number; hex?: string };
export type Facet =
  | { key: string; label: string; kind: "range"; unit: string; min: number | null; max: number | null }
  | { key: string; label: string; kind: "list" | "colors"; unit?: string; values: FacetValue[] };

export type ShowcaseCard = {
  series: string;
  name: string;
  brand: string;
  label: string;
  heightMm: number | null;
  priceFrom: number | null;
  image: ImageAsset | null;
  colors: ColorSwatch[];
};

export type ModelTile = { series: string; name: string; image: ImageAsset | null };

// key = "<трубы>-<подключение>", трубы 0 = без труб; подключения нет — "0-"
export type Execution = { key: string; tubes: number; connection: Connection | null; label: string; count: number };

export type VariantRow = {
  article: string;
  heightMm: number | null;
  widthMm: number | null;
  depthMm: number | null;
  lengthMm: number | null;
  axisMm: number | null;
  sections: number | null;
  powerW: number | null;
  areaM2: number | null; // 1 знак
  tubes: number | null;
  connection: Connection | null;
  thermovalve: boolean;
  orientation: "h" | "v" | "";
  mount: "wall" | "floor" | "";
  attrs: Record<string, string | number | boolean>;
  price: number | null; // целые BYN, с учётом выбранного цвета; null — по запросу
};

export type SeriesImage = ImageAsset & { color: string | null; orientation: "h" | "v" | "" };

export type SeriesDetail = {
  slug: string;
  name: string;
  category: string;
  brand: { slug: string; name: string; country: string };
  description: string; // html
  material: string;
  heating: "water" | "electric" | "combined";
  pressureBar: number | null;
  warrantyYears: number | null;
  videoUrl: string;
  images: SeriesImage[];
  files: { title: string; url: string }[];
  colorGroups: ColorGroup[];
  ranges: Record<string, [number | null, number | null]>;
  executions: Execution[];
  defaultExecution: string | null;
  columns: CatalogField[];
  filters: CatalogField[];
};
