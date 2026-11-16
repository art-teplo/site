import type { ReactNode } from "react";
import { cx } from "@/lib/format";
import { Reveal } from "@/components/Reveal/Reveal";
import { SplitText } from "@/components/SplitText/SplitText";
import styles from "./SectionHead.module.css";

type Props = {
  title: string;
  mark?: string; // часть заголовка на плашке
  titleId?: string;
  intro?: ReactNode;
  aside?: ReactNode; // справа от заголовка: ссылка «все», действие
  as?: "h1" | "h2";
  sideClassName?: string; // блок справа: секция может его переставить (шоурум с вертикальным видео)
  className?: string; // вся шапка: секция может поставить её в свою сетку (шоурум с вертикальным видео)
};

// Шапка секции: заголовок слева (слова выезжают из-под маски), вводный текст или действие справа.
// Без меток и номеров над заголовком — заголовок говорит сам.
export function SectionHead({ title, mark, titleId, intro, aside, as: Tag = "h2", sideClassName, className }: Props) {
  return (
    <header className={cx(styles.head, className)}>
      <Reveal className={styles.main} effect="mask">
        <Tag id={titleId} className={cx(styles.title, Tag === "h1" && styles.titleLg)}>
          <SplitText mark={mark}>{title}</SplitText>
        </Tag>
      </Reveal>
      {(intro || aside) && (
        <Reveal className={cx(styles.side, !intro && styles.sideEnd, sideClassName)} index={2}>
          {intro && <p className={styles.intro}>{intro}</p>}
          {aside}
        </Reveal>
      )}
    </header>
  );
}
