import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { getBrands, getCategories, getProjects, getSeries, getShowcases, getVariants } from "@/data/api";
import { formatPrice } from "@/lib/format";
import { seriesQuery, withoutHeight } from "@/lib/series-query";
import { LeadSection } from "@/sections/home/LeadSection";
import { SeriesAbout, seriesTabs } from "@/sections/series/SeriesAbout";
import { SeriesTabs } from "@/sections/series/SeriesTabs";
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
  // «от N» — тот же источник, что в шапке страницы (без выбранного цвета)
  const min = series.priceFrom;
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
  const [categories, brands, allProjects] = await Promise.all([getCategories(), getBrands(), getProjects()]);
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

  // Фото: изделие — в галерее первого экрана, интерьер — в своём разделе. Нет разметки kind — всё как изделие
  const interior = series.images.filter((i) => i.kind === "interior");
  const product = series.images.filter((i) => i.kind !== "interior");
  const gallery = product.length ? product : series.images;

  // Проекты и похожие отдаёт бэк; нет их в ответе (демо, старый бэк) — собираем сами
  const projects = series.projects?.length ? series.projects : allProjects.filter((p) => p.series.includes(series.slug));
  let similar = series.similar ?? [];
  if (!similar.length) {
    const showcase = await getShowcases(series.category, { brand: series.brand.slug, ranges: {}, lists: {} });
    const related = showcase.results.filter((c) => c.series !== series.slug);
    similar = related.filter((c, i) => related.findIndex((x) => x.series === c.series) === i).slice(0, 8);
  }
  const content = { series, interior, projects, similar };

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
        images={{ product: gallery, interior }}
        tabs={<SeriesTabs tabs={seriesTabs(content)} />}
      />
      <SeriesAbout {...content} category={category.slug} brandNames={Object.fromEntries(brands.map((b) => [b.slug, b.name]))} />
      <LeadSection source={`series/${series.slug}`} />
    </>
  );
}
