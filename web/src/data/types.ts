// Формы данных повторяют будущий API (Django + DRF). Когда появится бэкенд,
// файлы в src/data заменятся запросами, компоненты не изменятся.

export type ImageAsset = {
  src: string;
  width: number;
  height: number;
  alt: string;
};

export type CategorySlug = "radiatory" | "konvektory" | "polotentsesushiteli" | "armatura";

export type Category = {
  slug: CategorySlug;
  name: string;
  short: string;
  image: ImageAsset;
};

export type Brand = {
  slug: string;
  name: string;
  country: string;
  note: string;
  logo?: { src: string; width: number; height: number }; // с официальных сайтов производителей
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
  products: string[]; // Product.slug — связь необязательная
};

export type Faq = { q: string; a: string };

// Тело статьи — простые блоки; из админки придёт тем же списком
export type PostBlock = { h2: string } | { p: string } | { list: string[] };

export type Post = {
  slug: string;
  title: string;
  date: string;
  readMinutes: number;
  image: ImageAsset;
  lead: string;
  body: PostBlock[];
};

export type Service = {
  slug: string;
  title: string;
  text: string;
};
