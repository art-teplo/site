import { ProjectCard } from "@/components/ProjectCard/ProjectCard";
import { Container } from "@/components/Container/Container";
import { Reveal } from "@/components/Reveal/Reveal";
import { Schematic } from "@/components/PipeChips/PipeChips";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { ShowcaseCard } from "@/components/ShowcaseCard/ShowcaseCard";
import type { Project, SeriesDetail, ShowcaseCard as Card } from "@/data/types";
import { CONNECTION_LABEL, pipeGroup } from "@/lib/connections";
import styles from "./SeriesAbout.module.css";

type Props = { series: SeriesDetail; projects: Project[]; related: Card[]; category: string; brandNames: Record<string, string> };

const facts = (s: SeriesDetail): [string, string][] => {
  const heating = { water: "водяной", electric: "электрический", combined: "комбинированный" }[s.heating];
  return [
    ["Бренд", s.brand.country ? `${s.brand.name}, ${s.brand.country}` : s.brand.name],
    ...(s.material ? ([["Материал", s.material]] as [string, string][]) : []),
    ["Нагрев", heating],
    ...(s.pressureBar ? ([["Рабочее давление", `${s.pressureBar} бар`]] as [string, string][]) : []),
    ["Гарантия", s.warrantyYears ? `${s.warrantyYears} лет` : "[Уточнить у заказчика: срок гарантии]"],
  ];
};

// О серии: описание, исполнения и подключения, файлы, похожие серии.
// «В интерьерах» — проекты, где стоит серия; без проектов блока нет.
export function SeriesAbout({ series, projects, related, category, brandNames }: Props) {
  const connections = series.executions.filter((e) => e.connection);
  return (
    <>
      <Section labelledBy="about-title">
        <Container className={styles.layout}>
          <Reveal className={styles.text}>
            <h2 id="about-title" className={styles.title}>
              О серии
            </h2>
            {series.description ? <div className={styles.body} dangerouslySetInnerHTML={{ __html: series.description }} /> : null}
            {series.files.length > 0 && (
              <ul className={styles.files} aria-label="Файлы">
                {series.files.map((f) => (
                  <li key={f.url}>
                    <a href={f.url} target="_blank" rel="noopener noreferrer" className={styles.file}>
                      {f.title}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Reveal>
          <Reveal className={styles.side} index={1}>
            <table className={styles.facts}>
              <caption className="visually-hidden">Характеристики {series.name}</caption>
              <tbody>
                {facts(series).map(([k, v]) => (
                  <tr key={k}>
                    <th scope="row">{k}</th>
                    <td>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Reveal>
        </Container>
      </Section>

      {connections.length > 0 && (
        <Section tone="white" labelledBy="connect-title">
          <Container>
            <SectionHead titleId="connect-title" title="Как подключается" />
            <ul className={styles.executions}>
              {connections.map((e, i) => {
                const group = e.connection ? pipeGroup(e.connection) : null;
                return (
                  <Reveal as="li" key={e.key} index={i} className={styles.execution}>
                    {group && <Schematic group={group} />}
                    <span>
                      {e.connection ? CONNECTION_LABEL[e.connection] : e.label}
                      {e.tubes ? `, ${e.tubes}-трубное` : ""}
                    </span>
                  </Reveal>
                );
              })}
            </ul>
          </Container>
        </Section>
      )}

      {projects.length > 0 && (
        <Section tone="white" labelledBy="interiors-title">
          <Container>
            <SectionHead titleId="interiors-title" title="В интерьерах" />
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

      {related.length > 0 && (
        <Section labelledBy="related-title">
          <Container>
            <SectionHead titleId="related-title" title="Похожие серии" />
            <ul className={styles.related}>
              {related.map((card, i) => (
                <Reveal as="li" key={card.series} index={i}>
                  <ShowcaseCard card={card} category={category} brand={brandNames[card.brand]} sizes="(max-width: 767px) 50vw, 33vw" />
                </Reveal>
              ))}
            </ul>
          </Container>
        </Section>
      )}
    </>
  );
}
