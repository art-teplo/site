import type { ReactNode } from "react";
import styles from "./DataTable.module.css";

type Props = { caption?: string; head: string[]; rows: ReactNode[][]; note?: ReactNode };

// Таблица на волосяных линиях — сроки, гарантии, характеристики. На телефоне строки становятся карточками.
export function DataTable({ caption, head, rows, note }: Props) {
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        {caption && <caption className={styles.caption}>{caption}</caption>}
        <thead>
          <tr>
            {head.map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) =>
                j === 0 ? (
                  <th key={j} scope="row">
                    {cell}
                  </th>
                ) : (
                  <td key={j} data-label={head[j]}>
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {note && <p className={styles.note}>{note}</p>}
    </div>
  );
}
