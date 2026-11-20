import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { getBrands, getCategories, getLegacySeries, getProjects, getSeries, getShowcases, getVariants } from "@/data/api";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
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

// Меньше стольких товарных фото — первый экран добирает интерьерными
const HERO_MIN = 3;

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
  const urlParams = toParams(await searchParams);
  const series = await getSeries(slug);
  if (!series) {
    const legacy = categorySlug === "radiatory" ? await getLegacySeries(slug, urlParams.toString()) : null;
    if (!legacy?.choices.length) notFound();
    if (legacy.target) {
      const query = new URLSearchParams(urlParams);
      query.delete("o");
      if (legacy.execution) query.set("execution", legacy.execution);
      if (legacy.color) query.set("color", legacy.color);
      redirect(`/catalog/${categorySlug}/${legacy.target}${query.size ? `?${query}` : ""}`);
    }
    return <Section className={styles.top} labelledBy="series-title"><Container>
      <Breadcrumbs items={[{ href: "/", label: "Главная" }, { href: "/catalog/radiatory", label: "Радиаторы" }, { label: "Выберите исполнение" }]} />
      <h1 id="series-title" className={styles.legacyTitle}>Выберите исполнение радиатора</h1>
      <div className={styles.legacyGrid}>{legacy.choices.map((card) => <ShowcaseCard key={card.series} query={legacy.queries?.[card.series]} article={new URLSearchParams(legacy.queries?.[card.series]).get("v") ?? undefined} card={card} category={categorySlug} sizes="(max-width: 767px) 100vw, 50vw" />)}</div>
    </Container></Section>;
  }
  if (!series || series.category !== categorySlug) notFound();
  const [categories, brands, allProjects] = await Promise.all([getCategories(), getBrands(), getProjects()]);
  const category = categories.find((c) => c.slug === series.category);
  if (!category) notFound();

  // Первая страница по адресу; пустой результат по ?h — повод открыть таблицу без высоты
  const { query, fromH } = seriesQuery(urlParams, series);
  let initial = await getVariants(slug, { ...query, page: 1 });
  let dropped = false;
  if (fromH && initial.count === 0) {
    dropped = true;
    initial = await getVariants(slug, { ...withoutHeight(query), page: 1 });
  }

  // Фото: изделие — в галерее первого экрана, интерьер — в своём разделе. Нет разметки kind — всё как изделие
  const interior = series.images.filter((i) => i.kind === "interior");
  // Товарных меньше HERO_MIN — добираем интерьером, чтобы первый экран не был пустым.
  const product = series.images.filter((i) => !i.kind || i.kind === "product");
  const schemes = series.images.filter((i) => i.kind === "scheme");
  const gallery = product.length ? [...product, ...interior.slice(0, Math.max(0, HERO_MIN - product.length))] : series.images.filter((i) => i.kind !== "scheme");

  // Проекты и похожие отдаёт бэк; нет их в ответе (демо, старый бэк) — собираем сами
  const projects = series.projects?.length ? series.projects : allProjects.filter((p) => p.series.includes(series.slug));
  let similar = series.similar ?? [];
  if (!similar.length) {
    const showcase = await getShowcases(series.category, { brand: series.brand.slug, ranges: {}, lists: {} });
    const related = showcase.results.filter((c) => c.series !== series.slug);
    similar = related.filter((c, i) => related.findIndex((x) => x.series === c.series) === i).slice(0, 8);
  }
  const content = { series, interior, schemes, projects, similar };

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
        images={gallery}
        tabs={<SeriesTabs tabs={seriesTabs(content)} />}
      />
      <SeriesAbout {...content} category={category.slug} brandNames={Object.fromEntries(brands.map((b) => [b.slug, b.name]))} />
      <LeadSection source={`series/${series.slug}`} />
    </>
  );
}
