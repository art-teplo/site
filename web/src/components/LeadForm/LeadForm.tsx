"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/Button/Button";
import { Checkbox, ChoiceGroup, FileField, TextArea, TextField } from "@/components/Field/Field";
import { useSite } from "@/components/SiteProvider/SiteProvider";
import { cx } from "@/lib/format";
import styles from "./LeadForm.module.css";

const CONTACT_METHODS = ["Звонок", "Viber", "Telegram"] as const;
const METHOD_CODES: Record<string, string> = { Звонок: "call", Viber: "viber", Telegram: "telegram" };
const FILE_TYPES = ".pdf,.jpg,.jpeg,.png,.xls,.xlsx";
const MAX_FILE_MB = 50; // лимит Bot API на отправку файла в Telegram
const MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024; // как FileSizeValidator на бэке
// Версия текста согласия — сохраняется с заявкой (Закон РБ № 99-З). Поменяли текст у галочки — поднимите
const CONSENT_VERSION = "2026-11-04";
// Бэка нет (демо на Vercel, сборка без API_URL) — отправка имитируется. Флаг вшивает next.config.ts
const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";

type Props = {
  source: string; // откуда пришла заявка — видно менеджеру
  context?: string; // товар, ответы квиза, выбранный путь
  withFile?: boolean;
  submitLabel?: string;
  compact?: boolean;
  partner?: boolean; // анкета дизайнера/партнёра: студия и город
};

type Errors = Partial<Record<"name" | "phone" | "consent" | "file" | "form", string>>;
const FIELD_ERRORS = ["name", "phone", "consent", "file"] as const;

// Единая форма заявки (brief.md → «Заявка»): POST /api/leads/ → группа менеджеров в Telegram.
export function LeadForm({ source, context, withFile = true, submitLabel = "Отправить заявку", compact, partner }: Props) {
  const site = useSite();
  const [method, setMethod] = useState<string>(CONTACT_METHODS[0]);
  const [fileName, setFileName] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (form.get("website")) return; // honeypot

    const next: Errors = {};
    if (!String(form.get("name") ?? "").trim()) next.name = "Как к вам обращаться?";
    const digits = String(form.get("phone") ?? "").replace(/\D/g, "");
    // Грубая проверка: точную (коды операторов и городов) делает сервер
    if (!/^375\d{9}$/.test(digits)) next.phone = "Номер в формате +375 29 123-45-67";
    if (!form.get("consent")) next.consent = "Нужно согласие, иначе мы не сможем перезвонить";
    const file = form.get("file");
    if (file instanceof File && file.size > MAX_FILE_BYTES)
      next.file = `Файл больше ${MAX_FILE_MB} МБ. Вставьте ссылку на Яндекс.Диск или Google Drive в комментарий или пришлите файл в мессенджер, когда мы свяжемся`;
    setErrors(next);
    if (Object.keys(next).length) return;

    setState("sending");
    if (DEMO) {
      await new Promise((resolve) => setTimeout(resolve, 600));
      setState("sent");
      return;
    }

    form.set("contact_method", METHOD_CODES[method] ?? "call");
    form.delete("method");
    form.set("page", (window.location.pathname + window.location.search).slice(0, 300)); // бэк режет по 300
    form.set("consent_version", CONSENT_VERSION);
    // Пустое поле файла браузер всё равно шлёт — сервер счёл бы его пустым файлом
    if (file instanceof File && !file.size) form.delete("file");

    const failed = `Не получилось отправить. Позвоните нам: ${site.phone}`;
    try {
      const response = await fetch("/api/leads/", { method: "POST", body: form });
      if (response.ok) {
        setState("sent");
        return;
      }
      const serverErrors: Errors = {};
      if (response.status === 400) {
        const body: Record<string, string[]> = await response.json().catch(() => ({}));
        for (const key of FIELD_ERRORS) if (body[key]?.length) serverErrors[key] = body[key][0];
      }
      if (!Object.keys(serverErrors).length)
        serverErrors.form = response.status === 429 ? `Слишком много заявок подряд. Позвоните нам: ${site.phone}` : failed;
      setErrors(serverErrors);
    } catch {
      setErrors({ form: failed });
    }
    setState("idle");
  };

  if (state === "sent") {
    return (
      <div className={styles.sent} role="status">
        <p className={styles.sentTitle}>Заявка принята</p>
        <p className={styles.sentText}>{site.replyPromise}. Если удобнее — позвоните сами: <a href={site.phoneHref}>{site.phone}</a>.</p>
      </div>
    );
  }

  return (
    <form className={cx(styles.form, compact && styles.compact)} onSubmit={onSubmit} noValidate>
      <input type="hidden" name="source" value={source} />
      {context && <input type="hidden" name="context" value={context} />}
      <div className={styles.honeypot} aria-hidden="true">
        <label>
          Сайт <input type="text" name="website" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <div className={styles.row}>
        <TextField label="Имя" name="name" autoComplete="name" required error={errors.name} />
        <TextField
          label="Телефон"
          name="phone"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="+375 29 123-45-67"
          defaultValue="+375 "
          required
          error={errors.phone}
        />
      </div>

      {partner && (
        <div className={styles.row}>
          <TextField label="Студия или компания" name="company" autoComplete="organization" />
          <TextField label="Город" name="city" autoComplete="address-level2" defaultValue="Минск" />
        </div>
      )}

      <ChoiceGroup legend="Как связаться" name="method" options={CONTACT_METHODS} value={method} onChange={setMethod} />

      {!compact && <TextArea label="Комментарий" name="comment" placeholder="Площадь, число комнат, что уже выбрали" />}

      {withFile && (
        <FileField
          label="План, проект или спецификация"
          name="file"
          accept={FILE_TYPES}
          hint={`PDF, JPG, PNG, Excel до ${MAX_FILE_MB} МБ`}
          fileName={fileName}
          error={errors.file}
          onChange={(e) => setFileName(e.currentTarget.files?.[0]?.name ?? "")}
        />
      )}

      <Checkbox name="consent" error={errors.consent}>
        Согласен на обработку персональных данных, в том числе на передачу менеджерам через Telegram, по{" "}
        <Link href="/privacy">политике</Link>
      </Checkbox>

      {errors.form && (
        <p className={styles.formError} role="alert">
          {errors.form}
        </p>
      )}

      <div className={styles.actions}>
        <Button type="submit" arrow disabled={state === "sending"}>
          {state === "sending" ? "Отправляем…" : submitLabel}
        </Button>
        <p className={styles.promise}>{site.replyPromise}</p>
      </div>
    </form>
  );
}
