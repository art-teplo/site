// Формы данных повторяют будущий API (Django + DRF). Когда появится бэкенд,
// файлы в src/data заменятся запросами, компоненты не изменятся.

export type ImageAsset = {
  src: string;
  width: number;
  height: number;
  alt: string;
  // Точка фокуса из админки, проценты: что оставить в кадре, когда рамка обрезает фото. Нет — центр
  focus?: { x: number; y: number };
};

export type CategorySlug = "radiatory" | "konvektory" | "polotentsesushiteli" | "armatura";

// Категории и бренды — из админки (apps.catalog); товары пока в коде и ссылаются на них по slug
export type CategoryType = { slug: string; name: string; image: ImageAsset | null; seriesCount: number };

export type Category = {
  slug: string;
  name: string;
  short: string;
  image: ImageAsset; // товар без фона, PNG с прозрачностью
  seriesCount: number; // опубликованные серии
  types?: CategoryType[]; // подтипы («Стальные», «Биметаллические»…); нет — плитки типов не показываем
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

export type Project = {
  slug: string;
  title: string;
  place: string; // необязательное: пусто — подписи нет, только название
  image: ImageAsset;
  photos: ImageAsset[]; // ещё фото — листаются в галерее вместе с главным
  videoUrl?: string; // ролик проекта — вторым кадром галереи; пусто — нет
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
  | { key: string; label: string; kind: "range"; unit: string; has_unknown?: boolean; total_values?: number; min: number | null; max: number | null }
  | { key: string; label: string; kind: "list" | "colors"; unit?: string; has_unknown?: boolean; total_values?: number; values: FacetValue[] };

export type ShowcaseCard = {
  series: string;
  name: string;
  brand: string;
  category?: string; // Category.slug — приходит в поиске и «Похожих»
  label: string;
  priceFrom: number | null;
  image: ImageAsset | null;
  hoverImage?: ImageAsset | null; // второе фото: показывается при наведении
  type?: string | null; // CategoryType.slug
  colors: ColorSwatch[];
};

export type ModelTile = { series: string; name: string; image: ImageAsset | null };

// key = "<трубы>-<подключение>", трубы 0 = без труб; подключения нет — "0-"
export type Execution = { key: string; tubes: number; connection: Connection | null; label: string; count: number; mount?: "wall" | "floor" | null; thermovalve?: boolean | null; sourceId?: string };

export type VariantRow = {
  configurationLabel?: string;
  configurationKey?: string;
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
  thermovalve: boolean | null;
  orientation: "h" | "v" | "";
  mount: "wall" | "floor" | "";
  attrs: Record<string, string | number | boolean>;
  price: number | null; // целые BYN, с учётом выбранного цвета; null — по запросу
  // цена без цвета и id групп варианта (пусто — все группы серии): по ним цена пересчитывается
  // при смене цвета сразу, до ответа бэка. Нет — пересчёт ждёт запроса
  priceByn?: number | null;
  colorGroups?: number[];
};

// kind: product — фото изделия (галерея первого экрана), interior — в интерьере (раздел «В интерьере»),
// scheme — схема подключений и размеров (раздел «Подключения»); нет поля — product
export type SeriesImage = ImageAsset & { color: string | null; kind?: "product" | "interior" | "scheme" };

export type SeriesDetail = {
  factory_orientation?: "h" | "v" | null;
  editions?: {slug: string; orientation: "h" | "v" | null; label: string}[];
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
  ranges: Record<string, [number | null, number | null]>; // только для полей фильтра, не для цены «от»
  rangeSteps?: Record<string, number[]>; // реальные размеры всей серии, отдельно от страниц таблицы
  priceFrom: number | null; // «от» без выбранного цвета
  priceFromByGroup: Record<number, number | null>; // «от» при выбранном цвете, по id группы; null — по запросу
  executions: Execution[];
  defaultExecution: string | null;
  columns: CatalogField[];
  filters: CatalogField[];
  similar?: ShowcaseCard[]; // похожие серии; нет — без раздела
  projects?: Project[]; // проекты, где стоит серия (нет — страница берёт из общего списка)
};
