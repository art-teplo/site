import { Fragment, type CSSProperties, type ReactNode } from "react";
import styles from "./SplitText.module.css";

type Props = {
  children: ReactNode;
  // view — слова выезжают, когда предок <Reveal> получил data-visible; load — сразу при загрузке (hero)
  mode?: "view" | "load";
  mark?: string; // часть заголовка, выделенная плашкой (слова подряд, как в тексте)
};

// Заголовок, слова которого поднимаются из-под маски по очереди. Нестроковое содержимое выводится как есть.
export function SplitText({ children, mode = "view", mark }: Props) {
  if (typeof children !== "string") return <>{children}</>;
  const words = children.split(" ");
  const markWords = mark?.split(" ") ?? [];
  const last = markWords.length - 1;
  // Последнее слово выделения может быть началом слова заголовка: «ключ» в «ключ — »
  const fits = (w: string | undefined, m: string, j: number) => w === m || (j === last && !!w?.startsWith(m));
  const from = markWords.length ? words.findIndex((_, i) => markWords.every((m, j) => fits(words[i + j], m, j))) : -1;
  const to = from + markWords.length;
  const tail = from < 0 ? "" : words[to - 1].slice(markWords[last].length); // хвост после плашки, например « —»

  const word = (w: string, i: number) => (
    <span className={styles.word}>
      <span className={styles.inner} style={{ "--w": i } as CSSProperties}>
        {w}
      </span>
    </span>
  );
  const run = (list: string[], offset: number) =>
    list.map((w, i) => (
      <Fragment key={offset + i}>
        {word(w, offset + i)}
        {i < list.length - 1 && " "}
      </Fragment>
    ));

  return (
    <span className={mode === "load" ? styles.load : styles.view}>
      <span className="visually-hidden">{children}</span>
      {from < 0 ? (
        <span aria-hidden="true">{run(words, 0)}</span>
      ) : (
        <span aria-hidden="true">
          {from > 0 && <>{run(words.slice(0, from), 0)} </>}
          <span className={styles.nowrap}>
            <mark className={styles.mark}>{run([...words.slice(from, to - 1), markWords[last]], from)}</mark>
            {tail && word(tail, to - 1)}
          </span>
          {to < words.length && <> {run(words.slice(to), to)}</>}
        </span>
      )}
    </span>
  );
}
