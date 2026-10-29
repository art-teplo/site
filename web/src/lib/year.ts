import { cacheLife } from "next/cache";

// Текущий год для «N лет на рынке» и копирайта. Кэшируется: значение одно для всех посетителей,
// пересчитывается раз в сутки (Cache Components не разрешает new Date() в статической оболочке).
export async function currentYear() {
  "use cache";
  cacheLife("days");
  return new Date().getFullYear();
}
