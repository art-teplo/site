import type { Metadata } from "next";
import { SearchResults } from "@/sections/search/SearchResults";
import type { Sort } from "@/lib/catalog-query";

// Страница собирается под адрес (?q=): шапка читает usePathname() вне <Suspense>
export const instant = false;

export const metadata: Metadata = {
  title: "Поиск",
  description: "Поиск по каталогу радиаторов АртТепло.",
  robots: { index: false, follow: true }, // выдача поиска не нужна поисковикам и после запуска
};

export default async function PoiskPage({ searchParams }: PageProps<"/poisk">) {
  const { q, sort } = await searchParams;
  const query = (Array.isArray(q) ? q[0] : q)?.trim().slice(0, 100) ?? "";
  const order: "" | Sort = sort === "price" || sort === "-price" ? sort : "";
  return <SearchResults query={query} sort={order} />;
}
