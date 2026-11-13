import type { ReactNode } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { Breadcrumbs } from "@/components/Breadcrumbs/Breadcrumbs";
import { SplitText } from "@/components/SplitText/SplitText";
import { cx } from "@/lib/format";
import styles from "./PageIntro.module.css";

type Props = {
  title: string;
  intro?: ReactNode;
  crumbs?: { href?: string; label: string }[];
  children?: ReactNode; // якорное меню страницы или действия
  className?: string;
};

// Верх внутренней страницы: крошки, крупный заголовок, вводный текст и навигация по разделам страницы.
export function PageIntro({ title, intro, crumbs = [], children, className }: Props) {
  return (
    <Section className={cx(styles.intro, className)} labelledBy="page-title">
      <Container>
        <Breadcrumbs items={[{ href: "/", label: "Главная" }, ...crumbs, { label: title }]} />
        <div className={styles.head}>
          {/* Первый экран: анимация стартует сразу, без ожидания JS — не задерживает LCP */}
          <h1 id="page-title" className={styles.title}>
            <SplitText mode="load">{title}</SplitText>
          </h1>
          {intro && <p className={styles.text}>{intro}</p>}
        </div>
        {children && <div className={styles.extra}>{children}</div>}
      </Container>
    </Section>
  );
}

// Якорное меню по разделам страницы — пилюли под заголовком
export function AnchorNav({ items }: { items: { href: string; label: string }[] }) {
  return (
    <nav aria-label="На этой странице" className={styles.anchors}>
      {items.map((item) => (
        <a key={item.href} href={item.href} className={styles.anchor}>
          {item.label}
        </a>
      ))}
    </nav>
  );
}
