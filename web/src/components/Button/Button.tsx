import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost";

type Common = {
  children: ReactNode;
  variant?: Variant;
  arrow?: boolean;
  dot?: boolean; // красная точка, как у «Get in touch» в DGC
  block?: boolean;
  className?: string;
};

type AsLink = Common & { href: string } & Omit<ComponentPropsWithoutRef<"a">, "href" | "className" | "children">;
type AsButton = Common & { href?: undefined } & Omit<ComponentPropsWithoutRef<"button">, "className" | "children">;

// Одна кнопка на весь сайт. Цвета берёт из семантических токенов тона секции.
export function Button(props: AsLink | AsButton) {
  const { children, variant = "primary", arrow, dot, block, className, ...rest } = props;
  const classes = cx(styles.button, styles[variant], block && styles.block, className);
  const content = (
    <>
      {dot && <span className={styles.dot} aria-hidden="true" />}
      <span>{children}</span>
      {arrow && <Arrow />}
    </>
  );

  if ("href" in rest && rest.href !== undefined) {
    const { href, ...anchor } = rest as AsLink;
    const external = /^(https?:|tel:|mailto:|viber:)/.test(href);
    return external ? (
      <a href={href} className={classes} {...anchor}>
        {content}
      </a>
    ) : (
      <Link href={href} className={classes} {...anchor}>
        {content}
      </Link>
    );
  }

  const { type = "button", ...button } = rest as AsButton;
  return (
    <button type={type} className={classes} {...button}>
      {content}
    </button>
  );
}

export function Arrow({ className }: { className?: string }) {
  return (
    <svg className={cx(styles.arrow, className)} viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 10h11m0 0-4.5-4.5M15 10l-4.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
