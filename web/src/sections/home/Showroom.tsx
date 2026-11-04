import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Frame } from "@/components/Frame/Frame";
import { Picture } from "@/components/Picture/Picture";
import { Button } from "@/components/Button/Button";
import { Reveal } from "@/components/Reveal/Reveal";
import { getSite } from "@/data/api";
import styles from "./Showroom.module.css";

// 09 · Шоурум. Видео — постер с кнопкой (файл подставится позже, см. images-manifest.md);
// карта Яндекса — ссылкой, чтобы не грузить тяжёлый iframe на главной.
export async function Showroom() {
  const site = await getSite();
  return (
    <Section id="showroom" tone="dark" labelledBy="showroom-title">
      <Container>
        <SectionHead
          titleId="showroom-title"
          title="Приезжайте потрогать"
          intro="Радиатор на картинке и на стене — разные вещи. В шоуруме видно фактуру покраски, размер и как он греет."
        />
        <div className={styles.layout}>
          <Reveal className={styles.media}>
            <Frame ratio="16 / 9" corners parallax>
              <Picture
                image={{ src: "/images/showroom/showroom-poster.jpg", width: 1920, height: 1080, alt: "Шоурум АртТепло на Леонида Беды, 39" }}
                sizes="(max-width: 1023px) 100vw, 66vw"
              />
            </Frame>
            <span className={styles.play} aria-hidden="true">
              <span className={styles.playIcon} />
              Видео шоурума скоро
            </span>
          </Reveal>
          <Reveal className={styles.info} index={1}>
            <dl className={styles.list}>
              <div>
                <dt>Адрес</dt>
                <dd>
                  {site.city}, {site.address}
                </dd>
              </div>
              <div>
                <dt>Часы</dt>
                <dd>
                  {site.hours.map((h) => (
                    <span key={h.days} className={styles.hour}>
                      {h.days} <span>{h.time}</span>
                    </span>
                  ))}
                </dd>
              </div>
              <div>
                <dt>Телефон</dt>
                <dd>
                  <a href={site.phoneHref}>{site.phone}</a>
                </dd>
              </div>
            </dl>
            <div className={styles.actions}>
              <Button href={site.mapUrl} target="_blank" rel="noopener noreferrer" arrow dot>
                Приехать посмотреть
              </Button>
            </div>
          </Reveal>
        </div>
      </Container>
    </Section>
  );
}
