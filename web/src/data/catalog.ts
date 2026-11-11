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
  SeriesDetail,
  SeriesImage,
  ShowcaseCard,
  VariantRow,
} from "./types";

const img = (src: string, width: number, height: number, alt: string) => ({ src, width, height, alt });

export const categories: Omit<Category, "seriesCount">[] = [
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

export const brands: Omit<Brand, "seriesCount">[] = [
  { slug: "kzto", name: "КЗТО", country: "Россия", note: "Официальный представитель в Беларуси", logo: "/images/brands/kzto.png", warrantyYears: 10 },
  { slug: "guardo", name: "Guardo", country: "Россия", note: "Трубчатые радиаторы и полотенцесушители", logo: "/images/brands/guardo.svg", warrantyYears: 10 },
  { slug: "radimax", name: "Радимакс", country: "Россия", note: "Чугунные радиаторы Style Retro", logo: "/images/brands/radimax.png", warrantyYears: 10 },
  { slug: "royal-thermo", name: "Royal Thermo", country: "Италия", note: "Радиаторы", logo: "/images/brands/royal-thermo.svg", warrantyYears: 10 },
  { slug: "nova", name: "Nova", country: "Китай", note: "Трубчатые радиаторы", warrantyYears: 5 },
  { slug: "carisa", name: "Carisa", country: "", note: "Дизайн-радиаторы и полотенцесушители", logo: "/images/brands/carisa.png", warrantyYears: 3 },
  { slug: "sr", name: "SR Rubinetterie", country: "Италия", note: "Арматура и автоматика", warrantyYears: 5 },
];

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
    const key = `${tubes}-${row.connection ?? ""}`; // как у бэка: без подключения — пустая строка ("0-")
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
