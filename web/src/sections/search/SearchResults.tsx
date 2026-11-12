import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Reveal } from "@/components/Reveal/Reveal";
import { SearchForm } from "@/components/SearchForm/SearchForm";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
import { getBrands, getCategories, getSearch } from "@/data/api";
import { PageIntro } from "@/sections/page/PageIntro";
import styles from "./SearchResults.module.css";

// Поиск по каталогу: поле, сетка карточек витрины; пусто — спокойный текст и категории.
export async function SearchResults({ query }: { query: string }) {
  const [results, categories, brands] = await Promise.all([getSearch(query), getCategories(), getBrands()]);
  // Адрес серии строится по категории: карточка без неё не открылась бы
  const shown = results.filter((c) => c.category);
  const brandNames = Object.fromEntries(brands.map((b) => [b.slug, b.name]));
  const searched = query.length > 0;

  return (
    <>
      <PageIntro title="Поиск" intro="Название серии, бренд, тип или артикул." />
      <Section>
        <Container>
          <SearchForm key={query} defaultValue={query} className={styles.form} />
          {shown.length > 0 ? (
            <>
              <p className={styles.status} aria-live="polite">
                Найдено по запросу «{query}»: {shown.length}
              </p>
              <ul className={styles.grid}>
                {shown.map((card, i) => (
                  <li key={`${card.series}-${card.heightMm ?? i}`}>
                    <Reveal index={i % 4}>
                      <ShowcaseCard card={card} category={card.category!} brand={brandNames[card.brand]} />
                    </Reveal>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <div className={styles.empty}>
              <p className={styles.status} aria-live="polite">
                {searched && query.length < 2
                  ? "Введите хотя бы два символа."
                  : searched
                    ? `По запросу «${query}» ничего не нашли.`
                    : "Начните вводить название, бренд или артикул."}
              </p>
              <p className={styles.hint}>
                Попробуйте другое слово или откройте раздел каталога. Если не нашли нужное, позвоните или оставьте заявку: поможем подобрать.
              </p>
              <ul className={styles.categories}>
                {categories.map((c) => (
                  <li key={c.slug}>
                    <Link href={`/catalog/${c.slug}`} className={styles.category}>
                      {c.name.replace(/­/g, "")}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Container>
      </Section>
    </>
  );
}
