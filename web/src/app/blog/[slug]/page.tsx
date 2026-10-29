import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { SplitText } from "@/components/SplitText/SplitText";
import { getPost, posts } from "@/data/content";
import { formatDate } from "@/lib/format";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export function generateStaticParams() {
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: PageProps<"/blog/[slug]">): Promise<Metadata> {
  const post = getPost((await params).slug);
  return post ? { title: post.title, description: post.lead } : {};
}

export default async function PostPage({ params }: PageProps<"/blog/[slug]">) {
  const post = getPost((await params).slug);
  if (!post) notFound();
  const others = posts.filter((p) => p.slug !== post.slug);

  return (
    <>
      <Section className={styles.top} labelledBy="post-title">
        <Container>
          <Breadcrumbs items={[{ href: "/", label: "Главная" }, { href: "/blog", label: "Блог" }, { label: post.title }]} />
          <article className={styles.article}>
            <header className={styles.head}>
              <p className={styles.meta}>
                <time dateTime={post.date}>{formatDate(post.date)}</time> · {post.readMinutes} мин чтения
              </p>
              <h1 id="post-title" className={styles.title}>
                <SplitText mode="load">{post.title}</SplitText>
              </h1>
              <p className={styles.lead}>{post.lead}</p>
            </header>

            <Frame ratio="16 / 9" className={styles.cover}>
              <Picture image={post.image} sizes="(max-width: 1023px) 100vw, 1200px" eager />
            </Frame>

            <div className={styles.body}>
              {post.body.map((block, i) =>
                "h2" in block ? (
                  <h2 key={i}>{block.h2}</h2>
                ) : "list" in block ? (
                  <ul key={i}>
                    {block.list.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p key={i}>{block.p}</p>
                ),
              )}
            </div>
          </article>
        </Container>
      </Section>

      <Section tone="white" labelledBy="more-title">
        <Container>
          <h2 id="more-title" className={styles.moreTitle}>
            Ещё статьи
          </h2>
          <ul className={styles.more}>
            {others.map((p) => (
              <li key={p.slug} className={styles.card}>
                <Frame ratio="3 / 2">
                  <Picture image={p.image} sizes="(max-width: 767px) 100vw, 50vw" />
                </Frame>
                <p className={styles.meta}>
                  <time dateTime={p.date}>{formatDate(p.date)}</time> · {p.readMinutes} мин
                </p>
                <h3 className={styles.cardTitle}>
                  <Link href={`/blog/${p.slug}`} className={styles.cardLink}>
                    {p.title}
                  </Link>
                </h3>
              </li>
            ))}
          </ul>
        </Container>
      </Section>

      <LeadSection source={`blog:${post.slug}`} />
    </>
  );
}
