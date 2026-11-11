import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { getBrands, getCategories, getSeries, getShowcases, getVariants } from "@/data/api";
import { formatPrice } from "@/lib/format";
import { seriesQuery, withoutHeight } from "@/lib/series-query";
import { LeadSection } from "@/sections/home/LeadSection";
import { SeriesAbout } from "@/sections/series/SeriesAbout";
import { SeriesBody } from "@/sections/series/SeriesBody";
import styles from "./page.module.css";

// Страница собирается под адрес, без общей заготовки: в шапке и плавном скролле usePathname() вне
// <Suspense>, и после правки в админке Next не смог бы пересобрать заготовку — отдавал 500
export const instant = false;

const toParams = (raw: Record<string, string | string[] | undefined>) => {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(raw)) {
    const first = Array.isArray(value) ? value[0] : value;
    if (first !== undefined) params.set(key, first);
  }
  return params;
};

export async function generateMetadata({ params }: PageProps<"/catalog/[category]/[series]">): Promise<Metadata> {
  const { series: slug } = await params;
  const series = await getSeries(slug);
  if (!series) return {};
  // «от N» — тот же источник, что в шапке страницы: сводная цена серии, а нет её — минимум по строкам (без ?color цена в базовой группе цветов)
  let min = series.ranges.price?.[0] ?? null;
  if (min == null) {
    const rows = await getVariants(slug, { execution: series.defaultExecution ?? undefined, lists: {}, ranges: {} });
    const prices = rows.results.map((r) => r.price).filter((p): p is number => p != null);
    min = prices.length ? Math.min(...prices) : null;
  }
  const from = min != null ? ` Цена от ${formatPrice(min)}.` : "";
  return {
    title: `${series.name}, ${series.brand.name}`,
    description: `${series.name} — ${series.brand.name}. Размеры, подключения и цвета, цена под ваш вариант.${from}`,
    alternates: { canonical: `/catalog/${series.category}/${series.slug}` },
  };
}

export default async function SeriesPage({ params, searchParams }: PageProps<"/catalog/[category]/[series]">) {
  const { category: categorySlug, series: slug } = await params;
  const series = await getSeries(slug);
  if (!series || series.category !== categorySlug) notFound();
  const [categories, brands] = await Promise.all([getCategories(), getBrands()]);
  const category = categories.find((c) => c.slug === series.category);
  if (!category) notFound();

  // Первая страница по адресу; пустой результат по ?h — повод открыть таблицу без высоты
  const { query, fromH } = seriesQuery(toParams(await searchParams), series);
  let initial = await getVariants(slug, { ...query, page: 1 });
  let dropped = false;
  if (fromH && initial.count === 0) {
    dropped = true;
    initial = await getVariants(slug, { ...withoutHeight(query), page: 1 });
  }

  // Похожие: та же категория и бренд
  const showcase = await getShowcases(series.category, { brand: series.brand.slug, ranges: {}, lists: {} });
  const related = showcase.results.filter((c) => c.series !== series.slug);
  const unique = related.filter((c, i) => related.findIndex((x) => x.series === c.series) === i).slice(0, 3);

  return (
    <>
      <SeriesBody
        series={series}
        initial={{ ...initial, dropped }}
        breadcrumbs={
          <Breadcrumbs
            items={[
              { href: "/", label: "Главная" },
              { href: "/catalog", label: "Каталог" },
              { href: `/catalog/${category.slug}`, label: category.name },
              { label: series.name },
            ]}
          />
        }
        topClassName={styles.top}
      />
      <SeriesAbout series={series} related={unique} category={category.slug} brandNames={Object.fromEntries(brands.map((b) => [b.slug, b.name]))} />
      <LeadSection source={`series/${series.slug}`} />
    </>
  );
}
