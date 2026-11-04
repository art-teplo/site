import type { CSSProperties } from "react";
import { Button } from "@/components/Button/Button";
import { Picture } from "@/components/Picture/Picture";
import { SplitText } from "@/components/SplitText/SplitText";
import { getSite } from "@/data/api";
import styles from "./Hero.module.css";

// Где на фото светящиеся плафоны, в процентах кадра 1940×1201 — сюда ложится свечение ламп
const lamps = [
  { x: 17.7, y: 33 },
  { x: 15.9, y: 30 },
  { x: 21.8, y: 25 },
  { x: 19.2, y: 17 },
];

// Первый экран: вечерний интерьер. При загрузке комната в полумраке, лампы зажигаются по очереди,
// свет проявляет комнату, у радиатора остаётся тёплое «дыхание». При прокрутке кадр уходит с параллаксом.
export async function Hero() {
  const site = await getSite();
  return (
    <section className={styles.hero} data-tone="dark" aria-labelledby="hero-title">
      <div className={styles.stage}>
        <Picture
          className={styles.photo}
          image={{ src: "/images/hero/hero-desktop.jpg", width: 1940, height: 1201, alt: "Вечерняя спальня: у стены высокий трубчатый радиатор, над креслом подвесные лампы" }}
          sizes="(max-aspect-ratio: 1940/1201) 162vh, 100vw"
          eager
        />
        <span className={styles.dusk} aria-hidden="true" />
        <span className={styles.heat} aria-hidden="true" />
        <span className={styles.lamps} aria-hidden="true">
          {lamps.map((l, i) => (
            <i key={i} style={{ "--x": `${l.x}%`, "--y": `${l.y}%`, "--i": i } as CSSProperties} />
          ))}
        </span>
      </div>
      <span className={styles.scrim} aria-hidden="true" />

      <div className={styles.content}>
        <h1 id="hero-title" className={styles.title}>
          <SplitText mode="load">Тепло, которое хочется показать</SplitText>
          <span className={styles.dot}>.</span>
        </h1>
        <p className={styles.lead}>
          Шоурум дизайн-радиаторов в Минске с 2000 года. Подберём под интерьер и мощность, оформим замену и привезём.
        </p>
        <div className={styles.actions}>
          <Button href="/podbor" arrow>
            Подобрать радиатор
          </Button>
          <Button href="/catalog" variant="secondary">
            Каталог
          </Button>
        </div>
      </div>

      <p className={styles.meta}>{site.address}</p>
    </section>
  );
}
