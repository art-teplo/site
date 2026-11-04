import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getCategories } from "@/data/api";
import { productsIn } from "@/data/catalog";
import { CatalogPage } from "@/sections/catalog/CatalogPage";

const getCategory = async (slug: string) => (await getCategories()).find((c) => c.slug === slug);

export async function generateStaticParams() {
  return (await getCategories()).map((c) => ({ category: c.slug }));
}

export async function generateMetadata({ params }: PageProps<"/catalog/[category]">): Promise<Metadata> {
  const { category } = await params;
  const c = await getCategory(category);
  return c ? { title: `${c.name} — каталог`, description: `${c.name}: ${c.short.toLowerCase()}. Подбор и расчёт в шоуруме в Минске.` } : {};
}

export default async function CategoryPage({ params }: PageProps<"/catalog/[category]">) {
  const { category } = await params;
  const c = await getCategory(category);
  if (!c) notFound();
  return <CatalogPage category={c} products={productsIn(c.slug)} />;
}
