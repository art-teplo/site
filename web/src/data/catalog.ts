// ДЕМО-ДАННЫЕ. Серии взяты из списка для парсинга (materials/client/Забираем с Home-heat.docx),
// размеры, мощности и цены — условные, для вёрстки. Заменятся данными из админки.
import { CONNECTION_LABEL } from "@/lib/connections";
import { rowPrice } from "@/lib/price";
import type {
  Brand,
  CatalogField,
  Category,
  ColorGroup,
  Connection,
  Execution,
  Product,
  SeriesDetail,
  SeriesImage,
  ShowcaseCard,
  VariantRow,
} from "./types";

const img = (src: string, width: number, height: number, alt: string) => ({ src, width, height, alt });

export const categories: Category[] = [
  {
    slug: "radiatory",
    name: "Радиаторы",
    short: "Трубчатые, дизайн-радиаторы, чугунные",
    image: img("/images/categories/radiatory.png", 315, 241, "Трубчатый радиатор с термоголовкой"),
  },
  {
    slug: "konvektory",
    name: "Конвекторы",
    short: "Внутрипольные и напольные",
    image: img("/images/categories/konvektory.png", 800, 389, "Внутрипольный конвектор со свёрнутой решёткой"),
  },
  {
    slug: "polotentsesushiteli",
    name: "Полотенце\u00adсушители",
    short: "Водяные и электрические",
    image: img("/images/categories/polotentsesushiteli.png", 216, 229, "Водяной полотенцесушитель-лесенка"),
  },
  {
    slug: "armatura",
    name: "Арматура",
    short: "Вентили и автоматика",
    image: img("/images/categories/armatura.png", 190, 229, "Узел нижнего подключения радиатора"),
  },
];

export const brands: Brand[] = [
  { slug: "kzto", name: "КЗТО", country: "Россия", note: "Официальный представитель в Беларуси", logo: "/images/brands/kzto.png", warrantyYears: 10 },
  { slug: "guardo", name: "Guardo", country: "Россия", note: "Трубчатые радиаторы и полотенцесушители", logo: "/images/brands/guardo.svg", warrantyYears: 10 },
  { slug: "radimax", name: "Радимакс", country: "Россия", note: "Чугунные радиаторы Style Retro", logo: "/images/brands/radimax.png", warrantyYears: 10 },
  { slug: "royal-thermo", name: "Royal Thermo", country: "Италия", note: "Радиаторы", logo: "/images/brands/royal-thermo.svg", warrantyYears: 10 },
  { slug: "nova", name: "Nova", country: "Китай", note: "Трубчатые радиаторы", warrantyYears: 5 },
  { slug: "carisa", name: "Carisa", country: "", note: "Дизайн-радиаторы и полотенцесушители", logo: "/images/brands/carisa.png", warrantyYears: 3 },
  { slug: "sr", name: "SR Rubinetterie", country: "Италия", note: "Арматура и автоматика", warrantyYears: 5 },
];

const WHITE = { id: "white", name: "Белый RAL 9016", hex: "#f1f0ea" };
const BLACK = { id: "black", name: "Чёрный RAL 9005", hex: "#0e0e10" };
const GRAPHITE = { id: "graphite", name: "Графит RAL 7024", hex: "#474a50" };
const BRONZE = { id: "bronze", name: "Бронза", hex: "#6b4a2f" };
const CHROME = { id: "chrome", name: "Хром", hex: "#c9ccd1" };

const shots = (slug: string, name: string) => [
  img(`/images/products/${slug}/main.jpg`, 1200, 1500, `${name}, вид спереди`),
  img(`/images/products/${slug}/interior.jpg`, 1200, 1500, `${name} в интерьере`),
  img(`/images/products/${slug}/detail.jpg`, 1200, 1500, `${name}, деталь подключения`),
];

export const products: Product[] = [
  {
    slug: "guardo-retta-6p",
    name: "Guardo Retta 6P",
    brand: "guardo",
    category: "radiatory",
    type: "трубчатый",
    position: "вертикальный",
    material: "сталь",
    heating: "водяной",
    connections: ["нижнее", "боковое"],
    colors: [BLACK, WHITE, GRAPHITE],
    variants: [
      { id: "1500x300", heightMm: 1500, widthMm: 300, powerW: 820, priceByn: 1180 },
      { id: "1800x360", heightMm: 1800, widthMm: 360, powerW: 1150, priceByn: 1460 },
      { id: "2000x420", heightMm: 2000, widthMm: 420, powerW: 1440, priceByn: 1790 },
    ],
    depthMm: 60,
    axisMm: 50,
    pressureBar: 10,
    warrantyYears: 10,
    availability: "order",
    leadDays: 15,
    summary: "Прямоугольный профиль 30×60, вертикальная колонна, которая работает как деталь архитектуры.",
    images: shots("guardo-retta-6p", "Guardo Retta 6P"),
    videoUrl: "https://www.youtube.com/watch?v=VIDEO_ID",
    projects: ["kvartira-zelenyy-lug", "dom-zhdanovichi"],
  },
  {
    slug: "guardo-pilon",
    name: "Guardo Pilon",
    brand: "guardo",
    category: "radiatory",
    type: "трубчатый",
    position: "вертикальный",
    material: "сталь",
    heating: "водяной",
    connections: ["нижнее"],
    colors: [WHITE, BLACK],
    variants: [
      { id: "1200x250", heightMm: 1200, widthMm: 250, powerW: 560, priceByn: 890 },
      { id: "1800x320", heightMm: 1800, widthMm: 320, powerW: 980, priceByn: 1240 },
    ],
    depthMm: 70,
    axisMm: 50,
    pressureBar: 10,
    warrantyYears: 10,
    availability: "stock",
    summary: "Круглый профиль, мягкий силуэт. Подходит для узких простенков.",
    images: shots("guardo-pilon", "Guardo Pilon"),
    projects: ["kvartira-zelenyy-lug"],
  },
  {
    slug: "guardo-torre-4d",
    name: "Guardo Torre 4D",
    brand: "guardo",
    category: "radiatory",
    type: "трубчатый",
    position: "горизонтальный",
    material: "сталь",
    heating: "водяной",
    connections: ["боковое", "диагональное", "нижнее"],
    colors: [WHITE, GRAPHITE, BLACK],
    variants: [
      { id: "500x800", heightMm: 500, widthMm: 800, sections: 18, powerW: 1020, priceByn: 980 },
      { id: "500x1200", heightMm: 500, widthMm: 1200, sections: 27, powerW: 1530, priceByn: 1390 },
      { id: "300x1600", heightMm: 300, widthMm: 1600, sections: 36, powerW: 1250, priceByn: 1510 },
    ],
    depthMm: 140,
    axisMm: 450,
    pressureBar: 12,
    warrantyYears: 10,
    availability: "order",
    leadDays: 15,
    summary: "Четырёхтрубная классика под окно. Высокая мощность при малой высоте.",
    images: shots("guardo-torre-4d", "Guardo Torre 4D"),
    projects: ["dom-zhdanovichi", "zhk-minsk-mir"],
  },
  {
    slug: "kzto-quadrum",
    name: "КЗТО Quadrum",
    brand: "kzto",
    category: "radiatory",
    type: "профильный",
    position: "вертикальный",
    material: "сталь",
    heating: "водяной",
    connections: ["нижнее", "боковое"],
    colors: [BLACK, WHITE, BRONZE],
    variants: [
      { id: "1600x400", heightMm: 1600, widthMm: 400, powerW: 990, priceByn: 1640 },
      { id: "2000x500", heightMm: 2000, widthMm: 500, powerW: 1480, priceByn: 2120 },
    ],
    depthMm: 80,
    pressureBar: 15,
    warrantyYears: 10,
    availability: "request",
    summary: "Настенный и напольный дизайн-радиатор с квадратным профилем.",
    images: shots("kzto-quadrum", "КЗТО Quadrum"),
    projects: ["kvartira-nemiga", "dom-zhdanovichi"],
  },
  {
    slug: "kzto-vertikalnyy",
    name: "КЗТО вертикальный трубчатый",
    brand: "kzto",
    category: "radiatory",
    type: "трубчатый",
    position: "вертикальный",
    material: "сталь",
    heating: "водяной",
    connections: ["нижнее", "боковое", "диагональное"],
    colors: [WHITE, BLACK, GRAPHITE],
    variants: [
      { id: "1750x350", heightMm: 1750, widthMm: 350, sections: 8, powerW: 1100, priceByn: 1190 },
      { id: "2000x440", heightMm: 2000, widthMm: 440, sections: 10, powerW: 1520, priceByn: 1480 },
    ],
    depthMm: 105,
    axisMm: 50,
    pressureBar: 15,
    warrantyYears: 10,
    availability: "order",
    leadDays: 15,
    summary: "Секции собираются под размер простенка, любой цвет по RAL.",
    images: shots("kzto-vertikalnyy", "Вертикальный трубчатый радиатор КЗТО"),
    projects: ["zhk-minsk-mir"],
  },
  {
    slug: "radimax-style-retro",
    name: "Радимакс Style Retro",
    brand: "radimax",
    category: "radiatory",
    type: "секционный",
    position: "напольный",
    material: "чугун",
    heating: "водяной",
    connections: ["боковое", "диагональное"],
    colors: [BLACK, WHITE, BRONZE],
    variants: [
      { id: "6", heightMm: 640, widthMm: 480, sections: 6, powerW: 780, priceByn: 1320 },
      { id: "8", heightMm: 640, widthMm: 640, sections: 8, powerW: 1040, priceByn: 1720 },
      { id: "10", heightMm: 640, widthMm: 800, sections: 10, powerW: 1300, priceByn: 2110 },
    ],
    depthMm: 200,
    axisMm: 500,
    pressureBar: 12,
    warrantyYears: 10,
    availability: "order",
    leadDays: 30,
    summary: "Литой чугун с ретро-рельефом. Долго держит тепло и подходит к старому фонду.",
    images: shots("radimax-style-retro", "Чугунный радиатор Радимакс Style Retro"),
    projects: ["kvartira-nemiga"],
  },
  {
    slug: "nova-tube",
    name: "Nova трубчатый",
    brand: "nova",
    category: "radiatory",
    type: "трубчатый",
    position: "горизонтальный",
    material: "сталь",
    heating: "водяной",
    connections: ["боковое", "нижнее"],
    colors: [WHITE],
    variants: [
      { id: "500x1000", heightMm: 500, widthMm: 1000, sections: 22, powerW: 1180, priceByn: 640 },
      { id: "300x1400", heightMm: 300, widthMm: 1400, sections: 31, powerW: 1060, priceByn: 720 },
    ],
    depthMm: 101,
    axisMm: 450,
    pressureBar: 10,
    warrantyYears: 5,
    availability: "stock",
    summary: "Доступный трубчатый радиатор для замены под окном.",
    images: shots("nova-tube", "Трубчатый радиатор Nova"),
    projects: [],
  },
  {
    slug: "royal-thermo-sekcionnyy",
    name: "Royal Thermo секционный",
    brand: "royal-thermo",
    category: "radiatory",
    type: "секционный",
    position: "горизонтальный",
    material: "биметалл",
    heating: "водяной",
    connections: ["боковое", "нижнее"],
    colors: [WHITE, BLACK],
    variants: [
      { id: "6", heightMm: 574, widthMm: 480, sections: 6, powerW: 1020, priceByn: 410 },
      { id: "10", heightMm: 574, widthMm: 800, sections: 10, powerW: 1700, priceByn: 640 },
    ],
    depthMm: 87,
    axisMm: 500,
    pressureBar: 30,
    warrantyYears: 10,
    availability: "stock",
    summary: "Биметалл для центрального отопления многоэтажек.",
    images: shots("royal-thermo-sekcionnyy", "Секционный радиатор Royal Thermo"),
    projects: [],
  },
  {
    slug: "kzto-vnutripolnyy",
    name: "КЗТО внутрипольный конвектор",
    brand: "kzto",
    category: "konvektory",
    type: "внутрипольный",
    material: "сталь",
    heating: "водяной",
    connections: ["боковое"],
    colors: [GRAPHITE, BLACK],
    variants: [
      { id: "1500", heightMm: 110, widthMm: 1500, powerW: 1350, priceByn: 1580 },
      { id: "2500", heightMm: 110, widthMm: 2500, powerW: 2260, priceByn: 2390 },
    ],
    depthMm: 300,
    pressureBar: 15,
    warrantyYears: 10,
    availability: "order",
    leadDays: 20,
    summary: "Прячется в пол у панорамного окна и отсекает холод от стекла.",
    images: shots("kzto-vnutripolnyy", "Внутрипольный конвектор КЗТО"),
    projects: ["zhk-minsk-mir"],
  },
  {
    slug: "kzto-napolnyy",
    name: "КЗТО напольный конвектор",
    brand: "kzto",
    category: "konvektory",
    type: "напольный",
    material: "сталь",
    heating: "водяной",
    connections: ["нижнее"],
    colors: [BLACK, GRAPHITE, WHITE],
    variants: [
      { id: "1000", heightMm: 300, widthMm: 1000, powerW: 1120, priceByn: 1260 },
      { id: "1600", heightMm: 300, widthMm: 1600, powerW: 1790, priceByn: 1690 },
    ],
    depthMm: 200,
    pressureBar: 15,
    warrantyYears: 10,
    availability: "order",
    leadDays: 20,
    summary: "Низкий корпус у окна в пол, когда в стяжку уже не спрятать.",
    images: shots("kzto-napolnyy", "Напольный конвектор КЗТО"),
    projects: [],
  },
  {
    slug: "guardo-polotentsesushitel",
    name: "Guardo полотенцесушитель",
    brand: "guardo",
    category: "polotentsesushiteli",
    type: "лестница",
    material: "нержавеющая сталь",
    heating: "водяной",
    connections: ["нижнее", "боковое"],
    colors: [CHROME, BLACK, WHITE],
    variants: [
      { id: "800x500", heightMm: 800, widthMm: 500, powerW: 380, priceByn: 540 },
      { id: "1200x500", heightMm: 1200, widthMm: 500, powerW: 560, priceByn: 720 },
    ],
    depthMm: 100,
    pressureBar: 10,
    warrantyYears: 5,
    availability: "stock",
    summary: "Лестница из нержавеющей стали для водяной системы.",
    images: shots("guardo-polotentsesushitel", "Полотенцесушитель Guardo"),
    projects: ["kvartira-zelenyy-lug"],
  },
  {
    slug: "carisa-polotentsesushitel",
    name: "Carisa полотенцесушитель",
    brand: "carisa",
    category: "polotentsesushiteli",
    type: "дизайн",
    material: "алюминий",
    heating: "электрический",
    connections: ["скрытое"],
    colors: [BLACK, WHITE],
    variants: [
      { id: "1200x500", heightMm: 1200, widthMm: 500, powerW: 400, priceByn: 980 },
      { id: "1600x500", heightMm: 1600, widthMm: 500, powerW: 600, priceByn: 1240 },
    ],
    depthMm: 90,
    pressureBar: 0,
    warrantyYears: 3,
    availability: "request",
    summary: "Электрическая модель со скрытым подключением и терморегулятором.",
    images: shots("carisa-polotentsesushitel", "Полотенцесушитель Carisa"),
    projects: ["kvartira-nemiga"],
  },
  {
    slug: "sr-ventil-uglovoy",
    name: "SR вентиль угловой",
    brand: "sr",
    category: "armatura",
    type: "термостатический вентиль",
    material: "латунь",
    heating: "водяной",
    connections: ["угловое"],
    colors: [CHROME, BLACK, WHITE],
    variants: [{ id: "1/2", heightMm: 60, widthMm: 50, powerW: 0, priceByn: 120 }],
    depthMm: 50,
    pressureBar: 10,
    warrantyYears: 5,
    availability: "stock",
    summary: "Итальянский вентиль для трубчатых радиаторов, в цвет корпуса.",
    images: shots("sr-ventil-uglovoy", "Угловой вентиль SR Rubinetterie"),
    projects: [],
  },
  {
    slug: "radimax-armatura-retro",
    name: "Радимакс арматура Retro",
    brand: "radimax",
    category: "armatura",
    type: "комплект подключения",
    material: "латунь",
    heating: "водяной",
    connections: ["боковое"],
    colors: [BRONZE, BLACK],
    variants: [{ id: "set", heightMm: 80, widthMm: 60, powerW: 0, priceByn: 260 }],
    depthMm: 60,
    pressureBar: 10,
    warrantyYears: 5,
    availability: "order",
    leadDays: 30,
    summary: "Ретро-вентили и заглушки в тон чугунному радиатору.",
    images: shots("radimax-armatura-retro", "Ретро-арматура Радимакс"),
    projects: [],
  },
];

export const getProduct = (slug: string) => products.find((p) => p.slug === slug);
export const productsIn = (category: string) => products.filter((p) => p.category === category);
export const priceFrom = (p: Product) => Math.min(...p.variants.map((v) => v.priceByn));

// --- Демо нового каталога: те же 3 серии, что backend/src/apps/catalog/demo/demo.json ---
// Курсов в демо нет: priceByn — цены из demo.json в BYN по курсам на 11.11.2026
// (RUB 0.036399, EUR 3.3703, USD 3.0019 BYN за единицу, наценка 0), как считает бэк.

const RATES = { RUB: 0.036399, EUR: 3.3703, USD: 3.0019 };
const byn = (price: number, currency: keyof typeof RATES) => Math.round(price * RATES[currency] * 100) / 100;

// Поля категорий — как apps/catalog/schema.py (демо: радиаторы и полотенцесушители)
const f = (key: string, label: string, kind: CatalogField["kind"], unit = "", column = true): CatalogField => ({
  key,
  label,
  kind,
  unit,
  column,
  filter: true,
});
const COLOR_FIELD = { ...f("color", "Цвет", "colors"), column: false };
const BRAND_FIELD = { ...f("brand", "Бренд", "list"), column: false };
const FIELDS: Record<string, CatalogField[]> = {
  radiatory: [
    f("price", "Цена", "range", "BYN"),
    f("height", "Высота", "range", "мм"),
    f("width", "Ширина", "range", "мм"),
    f("depth", "Глубина", "range", "мм"),
    f("axis", "Межосевое", "range", "мм"),
    f("power", "Мощность", "range", "Вт"),
    f("area", "Площадь обогрева", "range", "м²"),
    f("sections", "Секции", "range"),
    f("tubes", "Трубность", "list"),
    f("connection", "Подключение", "list"),
    f("orientation", "Положение", "list"),
    COLOR_FIELD,
    BRAND_FIELD,
  ],
  polotentsesushiteli: [
    f("height", "Высота", "range", "мм"),
    f("width", "Ширина", "range", "мм"),
    f("power", "Мощность", "range", "Вт"),
    f("heating", "Тип нагрева", "list"),
    f("shape", "Форма", "list"),
    f("shelf", "Полочка", "list"),
    f("connection", "Подключение", "list"),
    COLOR_FIELD,
    BRAND_FIELD,
  ],
};
// Неизвестная категория — схема радиаторов, как на бэке
export const catalogFields = (category: string): CatalogField[] => FIELDS[category] ?? FIELDS.radiatory;

// Строка демо: VariantRow + то, из чего бэк считает цену
export type DemoVariant = VariantRow & { priceByn: number | null; colorGroups: number[] };

const demoRow = (
  article: string,
  dims: { h: number; w: number; d: number; axis: number; sections: number; power: number },
  rest: {
    price: number;
    currency: keyof typeof RATES;
    tubes?: number;
    connection?: Connection;
    orientation?: "h" | "v";
    attrs?: Record<string, string | number | boolean>;
  },
): DemoVariant => ({
  article,
  heightMm: dims.h,
  widthMm: dims.w,
  depthMm: dims.d,
  lengthMm: null,
  axisMm: dims.axis,
  sections: dims.sections,
  powerW: dims.power,
  areaM2: Math.round(dims.power / 10) / 10,
  tubes: rest.tubes ?? null,
  connection: rest.connection ?? null,
  thermovalve: false,
  orientation: rest.orientation ?? "",
  mount: "",
  attrs: rest.attrs ?? {},
  price: null, // демо считает цену при выдаче: price.ts/rowPrice
  priceByn: byn(rest.price, rest.currency),
  colorGroups: [],
});

const D = (h: number, w: number, d: number, axis: number, sections: number, power: number) => ({ h, w, d, axis, sections, power });
const nova = (article: string, dims: ReturnType<typeof D>, price: number) =>
  demoRow(article, dims, { price, currency: "RUB", tubes: 2, connection: "side" });
const retta = (article: string, dims: ReturnType<typeof D>, price: number, connection: Connection, orientation: "h" | "v") =>
  demoRow(article, dims, { price, currency: "RUB", connection, orientation });
const stretto = (article: string, dims: ReturnType<typeof D>, price: number) =>
  demoRow(article, dims, { price, currency: "USD", attrs: { heating: "water" } });

const photos = (dir: string, name: string): SeriesImage[] =>
  [
    ["main", "общий вид"],
    ["interior", "в интерьере"],
    ["detail", "деталь"],
  ].map(([file, what]) => ({ src: `/images/products/${dir}/${file}.jpg`, width: 1200, height: 1500, alt: `${name}: ${what}`, color: null, orientation: "" }));

const swatch = (code: string, name: string, hex: string, finish: string) => ({ code, name, hex, finish });
const group = (id: number, name: string, percent: number, isBase: boolean, anyRal: boolean, colors: ColorGroup["colors"]): ColorGroup => ({
  id,
  name,
  percent,
  isBase,
  anyRal,
  colors,
});
const anyRal = (id: number) => group(id, "Любой RAL", 0, false, true, []);

const BRAND_INFO: Record<string, SeriesDetail["brand"]> = {
  nova: { slug: "nova", name: "Nova", country: "Россия" },
  guardo: { slug: "guardo", name: "Guardo", country: "Россия" },
};

type DemoDef = {
  slug: string;
  name: string;
  brand: string;
  category: string;
  photoDir: string;
  groups: ColorGroup[];
  variants: DemoVariant[];
  showcases: { label: string; article: string }[];
};

const RETTA_COLORS = [
  swatch("RAL 1015", "RAL 1015 матовый", "#e6d2b5", "matte"),
  swatch("RAL 1015 глянец", "RAL 1015 глянец", "#e6d2b5", "gloss"),
  swatch("RAL 7040", "Серый матовый", "#9da3a6", "matte"),
  swatch("RAL 7040 глянец", "Серый глянец", "#9da3a6", "gloss"),
  swatch("RAL 9005", "Черный матовый", "#0a0a0a", "matte"),
  swatch("RAL 9005 глянец", "Черный глянцевый", "#0a0a0a", "gloss"),
  swatch("RAL 9016", "Белый матовый", "#f1f0ea", "matte"),
  swatch("RAL 9016 глянец", "Белый глянцевый", "#f1f0ea", "gloss"),
];

const DEFS: DemoDef[] = [
  {
    slug: "nova-siluet",
    name: "Nova Siluet",
    brand: "nova",
    category: "radiatory",
    photoDir: "nova-tube",
    groups: [
      group(1, "Стандартные", 0, true, false, [swatch("RAL 9010", "Белый молочный матовый RAL9010", "#f7f5eb", "matte")]),
      group(2, "Черный матовый +10 %", 10, false, false, [swatch("RAL 9005", "Черный матовый", "#0a0a0a", "matte")]),
    ],
    variants: [
      nova("NS-T2 300 4 S", D(300, 200, 70, 225, 4, 144), 5480),
      nova("NS-T2 300 5 S", D(300, 245, 70, 225, 5, 180), 6850),
      nova("NS-T2 1800 4 S", D(1800, 200, 70, 1725, 4, 824), 14996),
      nova("NS-T2 1800 5 S", D(1800, 245, 70, 1725, 5, 1030), 18745),
    ],
    showcases: [
      { label: "300 мм, боковое подключение", article: "NS-T2 300 4 S" },
      { label: "1800 мм, боковое подключение", article: "NS-T2 1800 5 S" },
    ],
  },
  {
    slug: "guardo-retta-3p",
    name: "Guardo Retta 3P",
    brand: "guardo",
    category: "radiatory",
    photoDir: "guardo-retta-6p",
    groups: [group(1, "Стандартные", 0, true, false, RETTA_COLORS), anyRal(2)],
    variants: [
      retta("3P-0500-08 NK-GOR-L", D(380, 500, 57, 50, 8, 429), 23543, "bottom_left", "h"),
      retta("3P-0500-08 BK-GOR", D(380, 500, 57, 350, 8, 429), 20543, "side", "h"),
      retta("3P-0600-08 NK-GOR-L", D(380, 600, 57, 50, 8, 498), 25510, "bottom_left", "h"),
      retta("3P-0600-08 BK-GOR", D(380, 600, 57, 350, 8, 498), 22510, "side", "h"),
      retta("3P-1800-02 NK-VER-L", D(1800, 80, 57, 50, 2, 328), 16456, "bottom_left", "v"),
      retta("3P-1800-02 BK-VER", D(1800, 80, 57, 1700, 2, 328), 13456, "side", "v"),
      retta("3P-1800-03 NK-VER-L", D(1800, 130, 57, 50, 3, 494), 20079, "bottom_left", "v"),
      retta("3P-1800-03 BK-VER", D(1800, 130, 57, 1700, 3, 494), 17079, "side", "v"),
    ],
    showcases: [
      { label: "Горизонтальный, 380 мм", article: "3P-0500-08 BK-GOR" },
      { label: "Вертикальный, 1800 мм", article: "3P-1800-02 BK-VER" },
    ],
  },
  {
    slug: "guardo-stretto",
    name: "Guardo Stretto",
    brand: "guardo",
    category: "polotentsesushiteli",
    photoDir: "guardo-polotentsesushitel",
    groups: [
      group(1, "Стандартные", 0, true, false, [
        swatch("RAL 9005", "Черный матовый", "#0a0a0a", "matte"),
        swatch("RAL 9016", "Белый матовый", "#f1f0ea", "matte"),
      ]),
      group(2, "Хром −4 %", -4, false, false, [swatch("Хром", "Хром", "#c0c4c8", "")]),
      anyRal(3),
    ],
    variants: [
      stretto("STRETTO 0685", D(600, 82, 87, 50, 2, 111), 164),
      stretto("STRETTO 0614", D(600, 140, 87, 108, 3, 165), 228),
      stretto("STRETTO 1285", D(1200, 82, 87, 50, 2, 219), 191),
      stretto("STRETTO 1214", D(1200, 140, 87, 108, 3, 326), 275),
    ],
    showcases: [
      { label: "Водяной, 600 мм", article: "STRETTO 0685" },
      { label: "Водяной, 1200 мм", article: "STRETTO 1285" },
    ],
  },
];

// Строка как её отдаёт API: без служебных полей демо, с ценой
export function publicRow(source: DemoVariant, price: number | null): VariantRow {
  const row: Partial<DemoVariant> = { ...source };
  delete row.priceByn;
  delete row.colorGroups;
  return { ...(row as VariantRow), price };
}

const floorInt = Math.floor;
function ranges(category: string, rows: DemoVariant[]): SeriesDetail["ranges"] {
  const value: Record<string, (r: DemoVariant) => number | null> = {
    price: (r) => r.priceByn,
    height: (r) => r.heightMm,
    width: (r) => r.widthMm,
    depth: (r) => r.depthMm,
    length: (r) => r.lengthMm,
    axis: (r) => r.axisMm,
    power: (r) => r.powerW,
    area: (r) => r.areaM2,
    sections: (r) => r.sections,
  };
  const result: SeriesDetail["ranges"] = {};
  for (const field of catalogFields(category)) {
    const get = value[field.key];
    if (field.kind !== "range" || !get) continue;
    const values = rows.map(get).filter((v): v is number => v != null);
    if (!values.length) {
      result[field.key] = [null, null];
    } else if (field.key === "area") {
      result[field.key] = [Math.min(...values), Math.max(...values)];
    } else {
      result[field.key] = [floorInt(Math.min(...values)), Math.ceil(Math.max(...values))];
    }
  }
  return result;
}

function executionsOf(rows: DemoVariant[]): Execution[] {
  const order: string[] = ["side", "diagonal", "bottom_left", "bottom_right", "bottom_universal", "bottom_ends", "bottom_center"];
  const merged = new Map<string, Execution>();
  for (const row of rows) {
    const tubes = row.tubes ?? 0;
    const key = `${tubes}-${row.connection ?? "None"}`; // как у бэка: None вместо пустого подключения
    const found = merged.get(key);
    if (found) found.count += 1;
    else {
      const parts = [tubes ? `${tubes}-трубный` : "", row.connection ? CONNECTION_LABEL[row.connection] : ""].filter(Boolean);
      merged.set(key, { key, tubes, connection: row.connection, label: parts.join(", ") || "Стандартное", count: 1 });
    }
  }
  return [...merged.values()].sort(
    (a, b) =>
      b.count - a.count ||
      b.tubes - a.tubes ||
      order.indexOf(a.connection ?? "") - order.indexOf(b.connection ?? ""),
  );
}

export const demoSeries: SeriesDetail[] = DEFS.map((def) => {
  const fields = catalogFields(def.category).filter((x) => x.key !== "brand");
  const executions = executionsOf(def.variants);
  return {
    slug: def.slug,
    name: def.name,
    category: def.category,
    brand: BRAND_INFO[def.brand],
    description: "",
    material: "",
    heating: "water",
    pressureBar: null,
    warrantyYears: 10,
    videoUrl: "",
    images: photos(def.photoDir, def.name),
    files: [],
    colorGroups: def.groups,
    ranges: ranges(def.category, def.variants),
    executions,
    defaultExecution: executions[0]?.key ?? null,
    columns: fields.filter((x) => x.column).map((x) => ({ ...x, filter: false })),
    filters: fields.filter((x) => x.filter).map((x) => ({ ...x, column: false })),
  };
});

// Строки с ценой «как у бэка»: без выбранного цвета — по базовой группе
export const demoVariants: Record<string, VariantRow[]> = Object.fromEntries(
  DEFS.map((def) => [
    def.slug,
    def.variants.map((v) => publicRow(v, rowPrice(v, def.groups))),
  ]),
);

export const demoSeriesBySlug = (slug: string) => demoSeries.find((s) => s.slug === slug);
// Исходные строки (priceByn, colorGroups) — для фильтрации и цены в выбранном цвете
export const demoSource = (slug: string): DemoVariant[] => DEFS.find((d) => d.slug === slug)?.variants ?? [];

// Карточки витрины: variantsOf — строки серии после фильтра (по умолчанию все).
// Витрина попадает в выдачу, если высота её варианта есть среди отфильтрованных; цена — минимум по этой высоте.
export function demoCards(
  category: string,
  variantsOf: (slug: string) => DemoVariant[] = demoSource,
  brands?: string[],
): ShowcaseCard[] {
  const cards: ShowcaseCard[] = [];
  for (const def of DEFS) {
    if (def.category !== category || (brands?.length && !brands.includes(def.brand))) continue;
    const rows = variantsOf(def.slug);
    if (!rows.length) continue;
    const series = demoSeries.find((s) => s.slug === def.slug)!;
    const colors = def.groups.flatMap((g) => g.colors);
    for (const showcase of def.showcases) {
      const height = def.variants.find((v) => v.article === showcase.article)?.heightMm ?? null;
      const same = height == null ? rows : rows.filter((r) => r.heightMm === height);
      if (!same.length) continue;
      const prices = same.map((r) => rowPrice(r, def.groups)).filter((p): p is number => p != null);
      cards.push({
        series: def.slug,
        name: def.name,
        brand: def.brand,
        label: showcase.label,
        heightMm: height,
        priceFrom: prices.length ? Math.min(...prices) : null,
        image: series.images[0],
        colors,
      });
    }
  }
  return cards;
}
