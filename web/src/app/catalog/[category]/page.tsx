import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { categories, getCategory, productsIn } from "@/data/catalog";
import { CatalogPage } from "@/sections/catalog/CatalogPage";

export function generateStaticParams() {
  return categories.map((c) => ({ category: c.slug }));
}

export async function generateMetadata({ params }: PageProps<"/catalog/[category]">): Promise<Metadata> {
  const { category } = await params;
  const c = getCategory(category);
  return c ? { title: `${c.name} — каталог`, description: `${c.name}: ${c.short.toLowerCase()}. Подбор и расчёт в шоуруме в Минске.` } : {};
}

export default async function CategoryPage({ params }: PageProps<"/catalog/[category]">) {
  const { category } = await params;
  const c = getCategory(category);
  if (!c) notFound();
  return <CatalogPage category={c} products={productsIn(c.slug)} />;
}
