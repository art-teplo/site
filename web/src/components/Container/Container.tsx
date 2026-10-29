import type { ElementType, ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Container.module.css";

type Props = { children: ReactNode; as?: ElementType; className?: string; grid?: boolean };

// Контейнер 1200px с боковыми полями. grid — 12-колоночная сетка внутри.
export function Container({ children, as: Tag = "div", className, grid }: Props) {
  return <Tag className={cx(styles.container, grid && styles.grid, className)}>{children}</Tag>;
}
