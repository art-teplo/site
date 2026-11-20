import Link from "next/link";
import { Suspense } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { SplitText } from "@/components/SplitText/SplitText";
import { getBrands, getCategories, getShowcasesFromUrl } from "@/data/api";
import type { Category } from "@/data/types";
import { cx } from "@/lib/format";
import { LeadSection } from "@/sections/home/LeadSection";
import { CategoryTiles } from "./CategoryTiles";
import { CatalogBrowser, CatalogFallback } from "./CatalogBrowser";
import styles from "./CatalogPage.module.css";

type Props = { category?: Category; initialKey?: string };

// Общий шаблон «Каталог» и «Каталог / категория».
export async function CatalogPage({ category, initialKey = "" }: Props) {
  const [categories, brands, initial] = await Promise.all([
    getCategories(),
    getBrands(),
    category ? getShowcasesFromUrl(category.slug, initialKey) : Promise.resolve(null),
  ]);
  const key = category?.slug ?? "all";
  return (
    <>
      <Section className={styles.top} labelledBy="catalog-title">
        <Container>
          <Breadcrumbs items={[{ href: "/", label: "Главная" }, category ? { href: "/catalog", label: "Каталог" } : { label: "Каталог" }, ...(category ? [{ label: category.name }] : [])]} />
          {/* key — при переходе между категориями шапка и список собираются заново и анимация проигрывается, как на других страницах */}
          <div key={`head-${key}`} className={styles.head}>
            <h1 id="catalog-title" className={styles.title}>
              <SplitText mode="load">{category ? category.name : "Каталог"}</SplitText>
            </h1>
            <p className={styles.intro}>
              Цены «от» — за минимальный размер. Точную цену под ваши размеры, цвет и подключение назовёт менеджер.
            </p>
          </div>
          <nav aria-label="Категории" className={styles.tabs}>
            <Link href="/catalog" className={cx(styles.tab, !category && styles.tabActive)} aria-current={!category ? "page" : undefined}>
              Все
            </Link>
            {categories.map((c) => (
              <Link
                key={c.slug}
                href={`/catalog/${c.slug}`}
                className={cx(styles.tab, category?.slug === c.slug && styles.tabActive)}
                aria-current={category?.slug === c.slug ? "page" : undefined}
              >
                {c.name}
              </Link>
            ))}
          </nav>
          <h2 className="visually-hidden">Товары</h2>
          <div key={`products-${key}`} className={styles.products}>
            {category && initial ? (
              <Suspense fallback={<CatalogFallback category={category} initial={initial} brands={brands} initialKey={initialKey} />}>
                <CatalogBrowser category={category} initial={initial} brands={brands} initialKey={initialKey} />
              </Suspense>
            ) : (
              <CategoryTiles categories={categories} />
            )}
          </div>
        </Container>
      </Section>
      <LeadSection source={category ? `catalog/${category.slug}` : "catalog"} />
    </>
  );
}
