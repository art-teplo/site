import type { CSSProperties } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { getPosts, getPromos } from "@/data/api";
import { cx, formatDate } from "@/lib/format";
import { PageIntro } from "@/sections/page/PageIntro";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Блог и акции",
  description: "Как выбрать радиатор, цвет и подключение: статьи и акции шоурума АртТепло.",
};

// Вертикальная карточка акции — узкая колонка по высоте, горизонтальная — как раньше, широкая
const isPortrait = (image: { width: number; height: number }) => image.height > image.width;

export default async function BlogPage() {
  const [posts, promos] = await Promise.all([getPosts(), getPromos()]);
  const [first, ...rest] = posts;
  return (
    <>
      <PageIntro title="Блог и акции" intro="Пишем о том, что спрашивают в шоуруме: как выбрать тип, мощность, цвет и подключение." />
      <Section tone="white">
        <Container>
          {/* Акции — над статьями, весь текст в карточке, своей страницы нет. Нет акций — нет и блока */}
          {promos.length > 0 && (
            <ul className={styles.promos} aria-label="Акции">
              {promos.map((promo, i) => (
                <Reveal as="li" key={promo.title} index={i}>
                  <article className={cx(styles.promo, isPortrait(promo.image) && styles.promoPortrait)}>
                    {/* Рамка — по форме самого фото: заказчица присылает готовые карточки акций (часто вертикальные),
                        их нельзя обрезать. Не крупнее исходника — маленькая картинка не растягивается в мыло */}
                    <div
                      className={styles.promoMedia}
                      style={{ "--promo-ratio": `${promo.image.width} / ${promo.image.height}`, "--promo-h": `${promo.image.height}px`, "--promo-w": `${promo.image.width}px` } as CSSProperties}
                    >
                      <Frame ratio={`${promo.image.width} / ${promo.image.height}`}>
                        <Picture image={promo.image} sizes="(max-width: 767px) 100vw, 40vw" />
                      </Frame>
                    </div>
                    <div className={styles.promoText}>
                      <p className={styles.meta}>
                        Акция ·{" "}
                        {promo.endsAt ? (
                          <>
                            до <time dateTime={promo.endsAt}>{formatDate(promo.endsAt)}</time>
                          </>
                        ) : (
                          "бессрочная"
                        )}
                      </p>
                      <h2 className={styles.promoTitle}>{promo.title}</h2>
                      <div className={styles.promoBody} dangerouslySetInnerHTML={{ __html: promo.body }} />
                    </div>
                  </article>
                </Reveal>
              ))}
            </ul>
          )}
          {/* В админке может не быть ни одной статьи — тогда вместо главной статьи заметка */}
          {first ? (
            <Reveal className={cx(styles.featured, styles.post)}>
              <Frame ratio="16 / 9">
                <Picture image={first.image} sizes="(max-width: 1023px) 100vw, 60vw" />
              </Frame>
              <div className={styles.featuredText}>
                <p className={styles.meta}>
                  <time dateTime={first.date}>{formatDate(first.date)}</time> · {first.readMinutes} мин
                </p>
                <h2 className={styles.featuredTitle}>
                  <Link href={`/blog/${first.slug}`} className={styles.link}>
                    {first.title}
                  </Link>
                </h2>
              </div>
            </Reveal>
          ) : (
            <p className={styles.note}>Статей пока нет.</p>
          )}
          <ul className={styles.list}>
            {rest.map((post, i) => (
              <Reveal as="li" key={post.slug} index={i}>
                <article className={styles.post}>
                  <Frame ratio="3 / 2">
                    <Picture image={post.image} sizes="(max-width: 767px) 100vw, 50vw" />
                  </Frame>
                  <p className={styles.meta}>
                    <time dateTime={post.date}>{formatDate(post.date)}</time> · {post.readMinutes} мин
                  </p>
                  <h2 className={styles.title}>
                    <Link href={`/blog/${post.slug}`} className={styles.link}>
                      {post.title}
                    </Link>
                  </h2>
                </article>
              </Reveal>
            ))}
          </ul>
        </Container>
      </Section>
      <LeadSection source="blog" />
    </>
  );
}
