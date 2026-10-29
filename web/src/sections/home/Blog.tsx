import Link from "next/link";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { Reveal } from "@/components/Reveal/Reveal";
import { posts } from "@/data/content";
import { formatDate } from "@/lib/format";
import styles from "./Blog.module.css";

// Блог: три свежие статьи, карточка целиком ведёт на статью.
export function Blog() {
  return (
    <Section tone="white" labelledBy="blog-title">
      <Container>
        <SectionHead titleId="blog-title" title="Разбираемся в отоплении" />
        <ul className={styles.list}>
          {posts.map((post, i) => (
            <Reveal as="li" key={post.slug} index={i}>
              <article className={styles.post}>
                <Frame ratio="3 / 2">
                  <Picture image={post.image} sizes="(max-width: 767px) 100vw, 33vw" />
                </Frame>
                <p className={styles.meta}>
                  <time dateTime={post.date}>{formatDate(post.date)}</time> · {post.readMinutes} мин
                </p>
                <h3 className={styles.title}>
                  <Link href={`/blog/${post.slug}`} className={styles.link}>
                    {post.title}
                  </Link>
                </h3>
              </article>
            </Reveal>
          ))}
        </ul>
      </Container>
    </Section>
  );
}
