import type { Connection } from "@/data/types";
import { CONNECTION_LABEL } from "./connections";

// Запасные подписи, если бэк прислал код вместо русского названия значения фильтра.
const WORDS: Record<string, string> = {
  water: "Водяной",
  electric: "Электрический",
  combined: "Комбинированный",
  steam: "Паровой",
  vertical: "Вертикальный",
  horizontal: "Горизонтальный",
  universal: "Универсальный",
  yes: "Да",
  no: "Нет",
  true: "Да",
  false: "Нет",
  wall: "Настенный",
  floor: "Напольный",
  steel: "Стальной",
  aluminium: "Алюминиевый",
  aluminum: "Алюминиевый",
  bimetal: "Биметаллический",
  cast_iron: "Чугунный",
  left: "Слева",
  right: "Справа",
  top: "Сверху",
  bottom: "Снизу",
};

const isCode = (s: string) => /^[a-z0-9_-]+$/.test(s);
const capital = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// Подпись значения фильтра: русская как пришла; код (water, bottom_left) — переводим
export function facetValueLabel(label: string, value: string): string {
  const raw = label || value;
  if (!isCode(raw)) return raw;
  const known = WORDS[raw] ?? CONNECTION_LABEL[raw as Connection];
  return known ? capital(known) : raw.replace(/[_-]+/g, " ");
}
