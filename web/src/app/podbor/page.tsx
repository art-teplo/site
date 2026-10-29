import type { Metadata } from "next";
import { Button } from "@/components/Button/Button";
import { PageIntro } from "@/sections/page/PageIntro";
import { Steps } from "@/sections/page/Steps";
import { Quiz } from "@/sections/home/Quiz";
import { LeadSection } from "@/sections/home/LeadSection";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Подбор радиатора",
  description: "Подберём радиатор под интерьер и мощность: по трём вопросам, плану квартиры, проекту дизайнера или готовой спецификации.",
};

// Подбор: сначала два входа (нет данных → квиз, есть план → форма с файлом), затем сам квиз,
// как проходит работа и форма для плана или спецификации.
export default function PodborPage() {
  return (
    <>
      <PageIntro
        title="Подбор радиатора"
        intro="Посчитаем мощность по комнатам, подберём размеры под простенки и предложим 2–3 варианта с ценами и сроками. Бесплатно."
      >
        <div className={styles.actions}>
          <Button href="#quiz" arrow>
            Ответить на 3 вопроса
          </Button>
          <Button href="#lead" variant="secondary">
            Отправить план или спецификацию
          </Button>
        </div>
      </PageIntro>
      <Quiz />
      <Steps />
      <LeadSection
        source="podbor"
        title="Пришлите план или спецификацию"
        text="Подойдёт план БТИ, проект дизайнера, спецификация в Excel или PDF, даже фото комнат с размерами. Посчитаем и перезвоним с вариантами."
      />
    </>
  );
}
