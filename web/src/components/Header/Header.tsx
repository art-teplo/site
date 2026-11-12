"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Icon } from "@/components/Icon/Icon";
import { SearchForm } from "@/components/SearchForm/SearchForm";
import { Logo } from "@/components/Logo/Logo";
import { Button } from "@/components/Button/Button";
import { getLenis } from "@/components/SmoothScroll/SmoothScroll";
import { menu, nav } from "@/data/site";
import { useSite } from "@/components/SiteProvider/SiteProvider";
import { cx } from "@/lib/format";
import styles from "./Header.module.css";

// Шапка: короткий ряд разделов наверху страницы; при прокрутке он уходит, остаётся «Меню»
// с полным списком разделов (как у radiator.center). Прозрачная поверх тёмного hero главной.
export function Header() {
  const site = useSite();
  const pathname = usePathname();
  const overHero = pathname === "/";
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchBtnRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // Закрываем меню при смене страницы
  const [prevPath, setPrevPath] = useState(pathname);
  if (pathname !== prevPath) {
    setPrevPath(pathname);
    setOpen(false);
    setSearchOpen(false);
  }

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const lenis = getLenis();
    if (open) {
      lenis?.stop();
      document.documentElement.style.overflow = "hidden";
      panelRef.current?.focus({ preventScroll: true });
    } else {
      lenis?.start();
      document.documentElement.style.overflow = "";
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  // Escape закрывает поиск и возвращает фокус на лупу
  useEffect(() => {
    if (!searchOpen) return;
    searchRef.current?.querySelector("input")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSearchOpen(false);
        searchBtnRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [searchOpen]);

  const dark = (overHero && !scrolled) || open || searchOpen;
  const close = () => setOpen(false);

  return (
    <header
      className={cx(styles.header, dark ? styles.onDark : styles.solid, (scrolled || open) && styles.compact, (open || searchOpen) && styles.open)}
      data-tone={dark ? "dark" : "light"}
    >
      <div className={styles.bar}>
        <Link href="/" className={styles.logo} aria-label="АртТепло, на главную" onClick={close}>
          <Logo />
        </Link>

        <nav className={styles.nav} aria-label="Основные разделы">
          <ul>
            {nav.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={styles.link}
                  aria-current={pathname.startsWith(item.href) ? "page" : undefined}
                  tabIndex={scrolled || open ? -1 : undefined}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.actions}>
          <a href={site.phoneHref} className={styles.phone}>
            {site.phone}
          </a>
          <button
            ref={searchBtnRef}
            type="button"
            className={styles.searchToggle}
            aria-expanded={searchOpen}
            aria-controls="site-search"
            aria-label={searchOpen ? "Закрыть поиск" : "Поиск по сайту"}
            onClick={() => {
              setOpen(false);
              setSearchOpen((v) => !v);
            }}
          >
            <Icon name={searchOpen ? "close" : "search"} className={styles.searchIcon} />
          </button>
          <Button href="/#lead" dot className={styles.cta} onClick={close}>
            Заявка
          </Button>
          <button
            ref={toggleRef}
            type="button"
            className={styles.toggle}
            aria-expanded={open}
            aria-controls="site-menu"
            onClick={() => {
              setSearchOpen(false);
              setOpen((v) => !v);
            }}
          >
            <span className={styles.toggleLabel}>{open ? "Закрыть" : "Меню"}</span>
            <span className={styles.toggleIcon} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div id="site-search" ref={searchRef} className={styles.search} hidden={!searchOpen}>
        <div className={styles.searchInner}>
          <SearchForm onSubmitted={() => setSearchOpen(false)} />
        </div>
      </div>

      {/* data-lenis-prevent: остановленный Lenis гасит касания на всей странице — панель листается сама */}
      <div id="site-menu" ref={panelRef} className={styles.panel} hidden={!open} tabIndex={-1} data-lenis-prevent>
        <div className={styles.panelInner}>
          <nav className={styles.groups} aria-label="Все разделы">
            {menu.map((group, i) => (
              <div key={group.title} className={styles.group} style={{ "--i": i } as CSSProperties}>
                <Link href={group.href} className={styles.groupTitle} onClick={close}>
                  {group.title}
                </Link>
                <ul className={styles.groupLinks}>
                  {group.links.map((link) => (
                    <li key={link.href}>
                      <Link href={link.href} className={styles.groupLink} onClick={close}>
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>

          <aside className={styles.contacts}>
            <a href={site.phoneHref} className={styles.contactsPhone}>
              {site.phone}
            </a>
            <p className={styles.contactsText}>
              {site.city}, {site.address}
              <br />
              {site.hours.map((h) => `${h.days} ${h.time}`).join(" · ")}
            </p>
            <div className={styles.messengers}>
              <a href={site.viber}>Viber</a>
              <a href={site.telegram}>Telegram</a>
              <a href={site.instagram} target="_blank" rel="noopener noreferrer">
                Instagram
              </a>
            </div>
            <Button href="/#lead" dot onClick={close}>
              Оставить заявку
            </Button>
          </aside>
        </div>
      </div>
    </header>
  );
}
