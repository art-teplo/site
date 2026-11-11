import type { ColorGroup, ColorSwatch } from "@/data/types";

// Выбранный ?color= среди групп серии. «Любой RAL» в адресе — any-<id группы> (так его отдаёт ColorSwatches).
export type PickedColor = { code: string; name: string; hex: string; anyRal: boolean; group: ColorGroup };

export function pickColor(groups: ColorGroup[], code: string | undefined): PickedColor | null {
  if (!code) return null;
  for (const group of groups) {
    if (group.anyRal && code === `any-${group.id}`) return { code, name: group.name || "Любой цвет RAL", hex: "", anyRal: true, group };
    const swatch: ColorSwatch | undefined = group.colors.find((c) => c.code === code);
    if (swatch) return { code, name: swatch.name, hex: swatch.hex, anyRal: false, group };
  }
  return null;
}

// На бэк «любой RAL» не уходит: цены в этом случае «по запросу» на самой странице
export const colorForApi = (code: string | undefined) => (code && !code.startsWith("any-") ? code : undefined);
