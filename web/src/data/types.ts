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
};

export type Brand = {
  slug: string;
  name: string;
  country: string; // пусто — не показываем
  note: string;
  logo?: { src: string; width: number; height: number }; // с официальных сайтов производителей
  warrantyYears: number | null; // «гарантия до»; пусто — бренда нет в таблице гарантий
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
  products: string[]; // Product.slug — связь необязательная
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
  showroomVideo: { src: string; poster: ImageAsset | null } | null; // файл из админки; нет — фото «скоро»
};

export type Service = {
  slug: string;
  title: string;
  text: string;
};
