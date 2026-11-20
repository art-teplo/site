import type { VariantRow } from "../data/types";

// Как на бирке: ширина × высота; у конвектора без высоты — длина × ширина.
export function variantSize(row: Pick<VariantRow, "heightMm" | "widthMm" | "lengthMm">): string {
  const pair = row.heightMm == null && row.lengthMm != null ? [row.lengthMm, row.widthMm] : [row.widthMm, row.heightMm];
  const parts = pair.filter((value): value is number => value != null);
  return parts.length ? `${parts.join("×")} мм` : "";
}
