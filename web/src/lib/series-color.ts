import type { ColorGroup, ColorSwatch } from "@/data/types";

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
    if (group.anyRal && code === `any-${group.id}`) return { code, name: group.name || "Любой цвет RAL", hex: "", anyRal: true, group };
    const swatch: ColorSwatch | undefined = group.colors.find((c) => c.code === code);
    if (swatch) return { code, name: colorLabel(swatch.name, swatch.code), hex: swatch.hex, anyRal: false, group };
  }
  return null;
}

// На бэк «любой RAL» не уходит: цены в этом случае «по запросу» на самой странице
export const colorForApi = (code: string | undefined) => (code && !code.startsWith("any-") ? code : undefined);
