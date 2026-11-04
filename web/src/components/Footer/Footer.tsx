import Link from "next/link";
import { Logo } from "@/components/Logo/Logo";
import { Container } from "@/components/Container/Container";
import { getCategories, getSite } from "@/data/api";
import { FOUNDED_YEAR, nav } from "@/data/site";
import { currentYear } from "@/lib/year";
import styles from "./Footer.module.css";

export async function Footer() {
  const [site, categories] = await Promise.all([getSite(), getCategories()]);
  const year = await currentYear();
  return (
    <footer className={styles.footer} data-tone="dark" id="contacts">
      <Container className={styles.inner}>
        <div className={styles.brand}>
          <Logo />
          <p className={styles.motto}>Продаём радиаторы, которые сами поставили бы себе домой.</p>
        </div>

        <div className={styles.col}>
          <p className={styles.heading}>Шоурум</p>
          <address className={styles.address}>
            {site.city}, {site.address}
          </address>
          <ul className={styles.hours}>
            {site.hours.map((h) => (
              <li key={h.days}>
                <span>{h.days}</span> {h.time}
              </li>
            ))}
          </ul>
          <a href={site.mapUrl} className={styles.link} target="_blank" rel="noopener noreferrer">
            Открыть в Яндекс.Картах
          </a>
        </div>

        <div className={styles.col}>
          <p className={styles.heading}>Связь</p>
          <a href={site.phoneHref} className={styles.phone}>
            {site.phone}
          </a>
          <a href={`mailto:${site.email}`} className={styles.link}>
            {site.email}
          </a>
          <div className={styles.row}>
            <a href={site.viber} className={styles.link}>
              Viber
            </a>
            <a href={site.telegram} className={styles.link}>
              Telegram
            </a>
            <a href={site.instagram} className={styles.link} target="_blank" rel="noopener noreferrer">
              Instagram
            </a>
          </div>
        </div>

        <nav className={styles.col} aria-label="Каталог">
          <p className={styles.heading}>Каталог</p>
          {categories.map((c) => (
            <Link key={c.slug} href={`/catalog/${c.slug}`} className={styles.link}>
              {c.name}
            </Link>
          ))}
        </nav>

        <nav className={styles.col} aria-label="Разделы">
          <p className={styles.heading}>Разделы</p>
          {nav.slice(1).map((item) => (
            <Link key={item.href} href={item.href} className={styles.link}>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className={styles.legal}>
          <p>
            © {FOUNDED_YEAR}–{year} {site.legalName}, УНП {site.unp}
          </p>
          <p>Информация на сайте не является публичной офертой. Цены «от» — ориентировочные.</p>
          <Link href="/privacy" className={styles.link}>
            Политика обработки персональных данных
          </Link>
        </div>
      </Container>
    </footer>
  );
}
