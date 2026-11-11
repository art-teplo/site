import type { Connection, VariantRow } from "@/data/types";

// Подписи — те же, что choices.Connection на бэке
export const CONNECTION_LABEL: Record<Connection, string> = {
  side: "боковое",
  diagonal: "диагональное",
  bottom_left: "нижнее левое",
  bottom_right: "нижнее правое",
  bottom_universal: "нижнее, слева или справа",
  bottom_ends: "нижнее по краям",
  bottom_center: "нижнее центральное",
  electric_left: "под электрику слева",
  electric_right: "под электрику справа",
};

export type PipeGroup = "side" | "bottom_edge" | "bottom_ends" | "bottom_center" | "diagonal";

// Группы подключений для схемы патрубков; «под электрику» в них не входит
export const PIPE_GROUPS: Record<PipeGroup, { label: string; connections: Connection[] }> = {
  side: { label: "Сбоку", connections: ["side"] },
  bottom_edge: { label: "Снизу у края", connections: ["bottom_left", "bottom_right", "bottom_universal"] },
  bottom_ends: { label: "Снизу по краям", connections: ["bottom_ends"] },
  bottom_center: { label: "Снизу по центру", connections: ["bottom_center"] },
  diagonal: { label: "По диагонали", connections: ["diagonal"] },
};

export function pipeGroup(c: Connection): PipeGroup | null {
  for (const key of Object.keys(PIPE_GROUPS) as PipeGroup[]) {
    if (PIPE_GROUPS[key].connections.includes(c)) return key;
  }
  return null;
}

const STEP = 50; // шаг между нижними патрубками, мм
const EDGE = 30; // отступ крайнего патрубка от края, мм

// Места патрубков на контуре в мм: x от левого края, y сверху. Пустой массив — схемы нет.
export function pipePoints(row: VariantRow): { x: number; y: number }[] {
  const { widthMm: w, heightMm: h, axisMm: axis } = row;
  if (!row.connection || w == null || h == null) return [];
  const group = pipeGroup(row.connection);
  const top = axis != null ? (h - axis) / 2 : null; // боковые патрубки симметричны относительно центра
  const bottomEdge = (left: boolean) => {
    const x = left ? EDGE : w - EDGE - STEP;
    return [
      { x, y: h },
      { x: x + STEP, y: h },
    ];
  };
  switch (group) {
    case "side":
      return top == null ? [] : [{ x: 0, y: top }, { x: 0, y: h - top }];
    case "diagonal":
      return top == null ? [] : [{ x: 0, y: top }, { x: w, y: h - top }];
    case "bottom_edge": {
      if (row.connection === "bottom_left") return bottomEdge(true);
      if (row.connection === "bottom_right") return bottomEdge(false);
      return [...bottomEdge(true), ...bottomEdge(false)];
    }
    case "bottom_ends":
      return [{ x: EDGE, y: h }, { x: w - EDGE, y: h }];
    case "bottom_center":
      return [{ x: w / 2 - STEP / 2, y: h }, { x: w / 2 + STEP / 2, y: h }];
    default:
      return [];
  }
}
