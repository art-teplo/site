import type { ColorGroup, ColorSwatch, SeriesImage } from "@/data/types";

// Выбранный ?color= среди групп серии. «Любой RAL» в адресе — any-<id группы> (так его отдаёт ColorSwatches).
export type PickedColor = { code: string; name: string; hex: string; anyRal: boolean; group: ColorGroup };

// Подпись цвета: название; « · RAL NNNN» добавляем, только если названия не содержит этого номера. Слово про отделку из кода не берём.
export function colorLabel(name: string, code: string): string {
  const ral = /\d{4}/.exec(code)?.[0];
  if (!ral || name.includes(ral)) return name;
  return `${name} · RAL ${ral}`;
}

export function pickColor(groups: ColorGroup[], code: string | undefined): PickedColor | null {
  if (!code) return null;
  for (const group of groups) {
    if (group.anyRal && (code === "any" || code === "any-ral" || code === `any-${group.id}`)) return { code, name: group.name || "Любой цвет RAL", hex: "", anyRal: true, group };
    const swatch: ColorSwatch | undefined = group.colors.find((c) => c.code === code);
    if (swatch) return { code, name: colorLabel(swatch.name, swatch.code), hex: swatch.hex, anyRal: false, group };
  }
  return null;
}

// На бэк «любой RAL» не уходит: цены в этом случае «по запросу» на самой странице
export const colorForApi = (code: string | undefined) => (code && !code.startsWith("any-") ? code : undefined);

// Глянец — отдельный цвет с тем же кодом и суффиксом (импорт прайса, GLOSS_SUFFIX в importers/parse.py):
// фото матового RAL 1015 показывает и глянцевый RAL 1015
const GLOSS_SUFFIX = " глянец";
const baseColor = (code: string) => (code.endsWith(GLOSS_SUFFIX) ? code.slice(0, -GLOSS_SUFFIX.length) : code);

export function matchesGalleryColor(image: SeriesImage, color: string): boolean {
  return Boolean(image.color && baseColor(image.color) === baseColor(color));
}

// Сортировка устойчивая: фото с одинаковым приоритетом идут в порядке из админки.
export function orderGalleryPhotos(images: SeriesImage[], color?: string): SeriesImage[] {
  const unique = images.filter((image, i) => images.findIndex((other) => other.src === image.src) === i);
  if (!color) return unique;
  const rank = (image: SeriesImage) => {
    if (image.color === color) return 0;
    return matchesGalleryColor(image, color) ? 1 : 2;
  };
  return unique.sort((a, b) => rank(a) - rank(b));
}
