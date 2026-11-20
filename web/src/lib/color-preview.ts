// «Любой RAL» сохраняет место в короткой палитре, остальные цвета доступны на странице серии.
export function colorPreview<T extends { code: string }>(colors: T[], limit: number): { visible: T[]; extra: number } {
  const ral = colors.find((color) => color.code === "any-ral");
  const visible = ral && !colors.slice(0, limit).includes(ral)
    ? [...colors.slice(0, Math.max(0, limit - 1)), ral]
    : colors.slice(0, limit);
  return { visible, extra: colors.length - visible.length };
}
