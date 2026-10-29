"use client";

import { useState } from "react";
import { Container } from "@/components/Container/Container";
import { Section } from "@/components/Section/Section";
import { SectionHead } from "@/components/SectionHead/SectionHead";
import { Button } from "@/components/Button/Button";
import { ChoiceGroup } from "@/components/Field/Field";
import { LeadForm } from "@/components/LeadForm/LeadForm";
import { quiz } from "@/data/content";
import styles from "./Quiz.module.css";

// Квиз «Подберём за 3 вопроса» (вопрос 2 к заказчику). В конце — та же форма заявки с ответами в контексте.
export function Quiz() {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const total = quiz.length;
  const done = step >= total;
  const current = quiz[Math.min(step, total - 1)];

  const context = quiz.map((q) => `${q.question} ${answers[q.id] ?? "—"}`).join("; ");

  return (
    <Section id="quiz" tone="dark" labelledBy="quiz-title">
      <Container className={styles.layout}>
        <SectionHead
          titleId="quiz-title"
          title="Ответьте на три вопроса — дальше считаем мы"
        />

        <div className={styles.panel}>
          <div className={styles.progress} aria-hidden="true">
            {quiz.map((q, i) => (
              <span key={q.id} className={styles.step} data-state={i < step ? "done" : i === step ? "active" : "todo"} />
            ))}
          </div>
          <p className={styles.counter} aria-live="polite">
            {done ? "Почти готово — куда прислать подбор?" : `Вопрос ${step + 1} из ${total}`}
          </p>

          {!done ? (
            <div key={current.id} className={styles.question}>
              <ChoiceGroup
                legend={current.question}
                name={`quiz-${current.id}`}
                options={current.options}
                value={answers[current.id] ?? ""}
                onChange={(value) => {
                  setAnswers((prev) => ({ ...prev, [current.id]: value }));
                  setStep((s) => s + 1);
                }}
                className={styles.choices}
              />
              {step > 0 && (
                <Button variant="ghost" onClick={() => setStep((s) => s - 1)}>
                  Назад
                </Button>
              )}
            </div>
          ) : (
            <div className={styles.question}>
              <p className={styles.summary}>
                {quiz.map((q) => answers[q.id]).join(" · ")}
              </p>
              <LeadForm source="quiz" context={context} withFile={false} compact submitLabel="Получить подбор" />
            </div>
          )}
        </div>
      </Container>
    </Section>
  );
}
