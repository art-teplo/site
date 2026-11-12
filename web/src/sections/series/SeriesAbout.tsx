import { Container } from "@/components/Container/Container";
import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import { Reveal } from "@/components/Reveal/Reveal";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
import type { Project, SeriesDetail, SeriesImage, ShowcaseCard as Card } from "@/data/types";
import { cx, plural } from "@/lib/format";
import { InteriorGallery } from "./InteriorGallery";
import styles from "./SeriesAbout.module.css";
import { SeriesVideo } from "./SeriesVideo";
import type { SeriesTab } from "./SeriesTabs";

type Content = { series: SeriesDetail; interior: SeriesImage[]; projects: Project[]; similar: Card[] };
type Props = Content & { category: string; brandNames: Record<string, string> };

const facts = (s: SeriesDetail): [string, string][] => {
  const heating = { water: "водяной", electric: "электрический", combined: "комбинированный" }[s.heating];
  return [
    ["Бренд", s.brand.country ? `${s.brand.name}, ${s.brand.country}` : s.brand.name],
    ...(s.material ? ([["Материал", s.material]] as [string, string][]) : []),
    ["Нагрев", heating],
    ...(s.pressureBar ? ([["Рабочее давление", `${s.pressureBar} бар`]] as [string, string][]) : []),
    ["Гарантия", s.warrantyYears ? plural(s.warrantyYears, "год", "года", "лет") : "[Уточнить у заказчика: срок гарантии]"],
  ];
};

// Разделы под таблицей — только те, где есть содержимое. Тот же список кормит полосу вкладок.
export function seriesTabs({ series, interior, projects, similar }: Content): SeriesTab[] {
  return [
    { id: "variants", label: "Варианты исполнения" },
    { id: "about", label: "О серии" },
    ...(interior.length ? [{ id: "interior", label: "В интерьере" }] : []),
    ...(series.videoUrl ? [{ id: "video", label: "Видеообзор" }] : []),
    ...(series.files.length ? [{ id: "files", label: "Файлы", count: series.files.length }] : []),
    ...(projects.length ? [{ id: "projects", label: "Проекты" }] : []),
    ...(similar.length ? [{ id: "similar", label: "Похожие" }] : []),
  ];
}

// О серии, фото в интерьере, видеообзор, файлы, проекты, похожие серии. Тон секций чередуется, начиная после таблицы.
export function SeriesAbout({ series, interior, projects, similar, category, brandNames }: Props) {
  let n = 0;
  const tone = () => (n++ % 2 === 0 ? "light" : "white");
  const hasText = Boolean(series.description);
  const rows = facts(series);

  return (
    <>
      <Section tone={tone()} id="about" labelledBy="about-title">
        <Container className={cx(styles.layout, !hasText && styles.compact)}>
          <Reveal className={styles.text}>
            <h2 id="about-title" className={styles.title}>
              О серии
            </h2>
            {hasText && <div className={styles.body} dangerouslySetInnerHTML={{ __html: series.description }} />}
          </Reveal>
          <Reveal className={styles.side} index={1}>
            {hasText ? (
              <table className={styles.facts}>
                <caption className="visually-hidden">Характеристики {series.name}</caption>
                <tbody>
                  {rows.map(([k, v]) => (
                    <tr key={k}>
                      <th scope="row">{k}</th>
                      <td>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <dl className={styles.factsRow}>
                {rows.map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            )}
          </Reveal>
        </Container>
      </Section>

      {interior.length > 0 && (
        <Section tone={tone()} id="interior" labelledBy="interior-title">
          <Container>
            <SectionHead titleId="interior-title" title="В интерьере" />
            <Reveal>
              <InteriorGallery images={interior} title={`${series.name} в интерьере`} />
            </Reveal>
          </Container>
        </Section>
      )}

      {series.videoUrl && (
        <Section tone={tone()} id="video" labelledBy="video-title">
          <Container>
            <SectionHead titleId="video-title" title="Видеообзор" />
            <Reveal>
              <SeriesVideo url={series.videoUrl} poster={series.images.find((i) => i.kind !== "interior") ?? series.images[0] ?? null} title={series.name} />
            </Reveal>
          </Container>
        </Section>
      )}

      {series.files.length > 0 && (
        <Section tone={tone()} id="files" labelledBy="files-title">
          <Container>
            <SectionHead titleId="files-title" title="Файлы" />
            <ul className={styles.files}>
              {series.files.map((f) => (
                <li key={f.url}>
                  <a href={f.url} target="_blank" rel="noopener noreferrer" className={styles.file}>
                    {f.title}
                  </a>
                </li>
              ))}
            </ul>
          </Container>
        </Section>
      )}

      {projects.length > 0 && (
        <Section tone={tone()} id="projects" labelledBy="projects-title">
          <Container>
            <SectionHead titleId="projects-title" title="Проекты" />
            <ul className={styles.projects}>
              {projects.map((p, i) => (
                <Reveal as="li" key={p.slug} index={i}>
                  <ProjectCard project={p} ratio="4 / 3" sizes="(max-width: 767px) 100vw, 33vw" />
                </Reveal>
              ))}
            </ul>
          </Container>
        </Section>
      )}

      {similar.length > 0 && (
        <Section tone={tone()} id="similar" labelledBy="similar-title">
          <Container>
            <SectionHead titleId="similar-title" title="Похожие серии" />
            <ul className={styles.related}>
              {similar.slice(0, 4).map((card, i) => (
                <Reveal as="li" key={card.series} index={i}>
                  <ShowcaseCard card={card} category={category} brand={brandNames[card.brand]} sizes="(max-width: 767px) 50vw, (max-width: 1023px) 33vw, 25vw" />
                </Reveal>
              ))}
            </ul>
          </Container>
        </Section>
      )}
    </>
  );
}
