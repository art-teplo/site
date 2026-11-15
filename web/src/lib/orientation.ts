// Ориентация радиатора на фото и у витрины: h — горизонтальный, v — вертикальный.
// С карточки витрины она приходит в адресе (?o=), и фото этой ориентации на странице серии идут первыми.
export type Orientation = "h" | "v";

export const parseOrientation = (value: string | null | undefined): Orientation | undefined =>
  value === "h" || value === "v" ? value : undefined;

// 0 — фото этой ориентации (или цели нет), 1 — фото без ориентации, 2 — другой ориентации
export function orientationRank(photo: string, target: string | undefined): number {
  if (!target || photo === target) return 0;
  return photo ? 2 : 1;
}

// Фото по ориентации, порядок внутри — как в админке; ни одно фото не пропадает
export const byOrientation = <T extends { orientation: string }>(images: T[], target: string | undefined): T[] =>
  target ? images.map((im, i) => ({ im, i, r: orientationRank(im.orientation, target) })).sort((a, b) => a.r - b.r || a.i - b.i).map((x) => x.im) : images;
