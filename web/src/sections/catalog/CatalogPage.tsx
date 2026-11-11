import Link from "next/link";
import { Suspense } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { SplitText } from "@/components/SplitText/SplitText";
import { getBrands, getCategories, getShowcases } from "@/data/api";
import type { Category } from "@/data/types";
import { cx } from "@/lib/format";
import { LeadSection } from "@/sections/home/LeadSection";
import { CatalogBrowser, CatalogFallback } from "./CatalogBrowser";
import styles from "./CatalogPage.module.css";

type Props = { category?: Category };

// Общий шаблон «Каталог» и «Каталог / категория».
export async function CatalogPage({ category }: Props) {
  const [categories, brands, initial] = await Promise.all([
    getCategories(),
    getBrands(),
    category ? getShowcases(category.slug, { ranges: {}, lists: {} }) : Promise.resolve(null),
  ]);
  const key = category?.slug ?? "all";
  return (
    <>
      <Section className={styles.top} labelledBy="catalog-title">
        <Container>
          <Breadcrumbs items={[{ href: "/", label: "Главная" }, category ? { href: "/catalog", label: "Каталог" } : { label: "Каталог" }, ...(category ? [{ label: category.name }] : [])]} />
          {/* key — при переходе между категориями шапка и список собираются заново и анимация проигрывается, как на других страницах */}
          <div key={key} className={styles.head}>
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
          <div key={key} className={styles.products}>
            {category && initial ? (
              <Suspense fallback={<CatalogFallback category={category} initial={initial} brands={brands} />}>
                <CatalogBrowser category={category} initial={initial} brands={brands} />
              </Suspense>
            ) : (
              <ul className={styles.categories}>
                {categories.map((c) => (
                  <li key={c.slug}>
                    <Link href={`/catalog/${c.slug}`} className={styles.categoryLink}>
                      <span className={styles.categoryName}>{c.name}</span>
                      <span className={styles.categoryShort}>{c.short}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Container>
      </Section>
      <LeadSection source={category ? `catalog/${category.slug}` : "catalog"} />
    </>
  );
}
