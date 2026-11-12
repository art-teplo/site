"use client";

import Link from "next/link";
import { useState } from "react";
import { Frame } from "@/components/Frame/Frame";
import { Lightbox } from "@/components/Lightbox/Lightbox";
import { Picture } from "@/components/Picture/Picture";
import { Arrow, Button } from "@/components/Button/Button";
import type { Project } from "@/data/types";
import { cx } from "@/lib/format";
import styles from "./ProjectsSlider.module.css";

const KIND: Record<Project["kind"], string> = { квартира: "Квартира", дом: "Дом", ЖК: "Жилой комплекс" };

// Проекты по одному со стрелками: кадр, описание и стрелки. Главная на телефоне вместо ленты (sections/home/Projects)
type Props = { projects: Project[]; seriesLinks: Record<string, { name: string; href: string }> };

export function ProjectsSlider({ projects, seriesLinks }: Props) {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState<1 | -1>(1);
  const p = projects[index];
  if (!p) return null;
  const stands = p.series.flatMap((slug) => (seriesLinks[slug] ? [seriesLinks[slug]] : []));
  const go = (step: 1 | -1) => {
    setDir(step);
    setIndex((i) => (i + step + projects.length) % projects.length);
  };
  const frame = (
    <Frame ratio="3 / 2">
      <Picture image={p.image} sizes="(max-width: 767px) 100vw, 60vw" />
    </Frame>
  );

  const shift = dir === 1 ? styles.fromRight : styles.fromLeft;
  const photo = (
    <div className={styles.photo}>
      {p.photos.length > 0 ? (
        <Lightbox images={[p.image, ...p.photos]} title={p.title}>
          {frame}
        </Lightbox>
      ) : (
        frame
      )}
    </div>
  );
  const info = (
    <div className={styles.info}>
      <span className={styles.meta}>
        {KIND[p.kind]} · {p.place}
      </span>
      <h3 className={styles.title}>{p.title}</h3>
      {stands.length > 0 && (
        <div className={styles.stands}>
          <span className={styles.meta}>Что стоит в проекте</span>
          <span className={styles.standsList}>
            {stands.map((s) => (
              <Link key={s.href} href={s.href} className={styles.stand}>
                {s.name}
              </Link>
            ))}
          </span>
        </div>
      )}
    </div>
  );
  const controls = (
    <div className={styles.controls}>
      <button type="button" className={cx(styles.nav, styles.prev)} onClick={() => go(-1)} aria-label="Предыдущий проект">
        <Arrow />
      </button>
      <span className={styles.counter} aria-live="polite">
        {index + 1} / {projects.length}
      </span>
      <button type="button" className={styles.nav} onClick={() => go(1)} aria-label="Следующий проект">
        <Arrow />
      </button>
      <Button href="/proekty" variant="ghost" arrow className={styles.all}>
        Все проекты
      </Button>
    </div>
  );

  const stage = (
    <div className={styles.stage}>
      {/* key — новый кадр перезапускает анимацию появления */}
      <div key={p.slug} className={cx(styles.slide, shift)}>
        {photo}
        {info}
      </div>
      {controls}
    </div>
  );
  return stage;
}
