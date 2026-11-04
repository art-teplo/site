import type { CSSProperties, ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Frame.module.css";

type Props = {
  children: ReactNode;
  ratio?: string; // "4 / 5", "16 / 9"
  parallax?: boolean;
  rounded?: boolean;
  className?: string;
};

// Рамка для медиа: пропорции, скругление и лёгкий параллакс содержимого.
export function Frame({ children, ratio, parallax, rounded = true, className }: Props) {
  return (
    <div
      className={cx(styles.frame, rounded && styles.rounded, parallax && styles.parallax, className)}
      style={ratio ? ({ "--ratio": ratio } as CSSProperties) : undefined}
    >
      <div className={styles.media}>{children}</div>
    </div>
  );
}
