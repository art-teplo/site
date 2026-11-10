import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { getPosts } from "@/data/api";
import { cx, formatDate } from "@/lib/format";
import { PageIntro } from "@/sections/page/PageIntro";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Блог и акции",
  description: "Как выбрать радиатор, цвет и подключение: статьи шоурума АртТепло.",
};

export default async function BlogPage() {
  const posts = await getPosts();
  const [first, ...rest] = posts;
  return (
    <>
      <PageIntro title="Блог и акции" intro="Пишем о том, что спрашивают в шоуруме: как выбрать тип, мощность, цвет и подключение." />
      <Section tone="white">
        <Container>
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
          <p className={styles.note}>Акций сейчас нет. Когда появятся — будут здесь, без таймеров и «последнего дня».</p>
        </Container>
      </Section>
      <LeadSection source="blog" />
    </>
  );
}
