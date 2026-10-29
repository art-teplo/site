import type { ComponentPropsWithoutRef, ReactNode } from "react";
import { cx } from "@/lib/format";
import styles from "./Field.module.css";

type FieldProps = {
  label: string;
  name: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children?: ReactNode;
};

type InputProps = FieldProps & Omit<ComponentPropsWithoutRef<"input">, "name">;

export function TextField({ label, name, error, hint, required, className, ...input }: InputProps) {
  const id = `f-${name}`;
  return (
    <div className={cx(styles.field, className)}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </label>
      <input
        id={id}
        name={name}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined}
        className={styles.input}
        {...input}
      />
      {hint && !error && (
        <p id={`${id}-hint`} className={styles.hint}>
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-err`} className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function TextArea({ label, name, className, ...rest }: FieldProps & Omit<ComponentPropsWithoutRef<"textarea">, "name">) {
  const id = `f-${name}`;
  return (
    <div className={cx(styles.field, className)}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <textarea id={id} name={name} rows={3} className={cx(styles.input, styles.textarea)} {...rest} />
    </div>
  );
}

type ChoiceProps = {
  legend: string;
  name: string;
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
};

// Выбор одного варианта пилюлями (способ связи, ответы квиза).
export function ChoiceGroup({ legend, name, options, value, onChange, className }: ChoiceProps) {
  return (
    <fieldset className={cx(styles.fieldset, className)}>
      <legend className={styles.label}>{legend}</legend>
      <div className={styles.choices}>
        {options.map((option) => (
          <label key={option} className={styles.choice}>
            <input
              type="radio"
              name={name}
              value={option}
              checked={value === option}
              onChange={() => onChange(option)}
              className={styles.choiceInput}
            />
            <span className={styles.choiceLabel}>{option}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function Checkbox({ name, children, error, ...rest }: { name: string; children: ReactNode; error?: string } & Omit<ComponentPropsWithoutRef<"input">, "name" | "type" | "children">) {
  const id = `f-${name}`;
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.check}>
        <input id={id} type="checkbox" name={name} className={styles.checkInput} aria-invalid={error ? true : undefined} {...rest} />
        <span className={styles.checkBox} aria-hidden="true" />
        <span className={styles.checkText}>{children}</span>
      </label>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function FileField({ label, name, hint, fileName, error, ...rest }: FieldProps & { fileName?: string } & Omit<ComponentPropsWithoutRef<"input">, "name" | "type">) {
  const id = `f-${name}`;
  return (
    <div className={styles.field}>
      <span className={styles.label}>{label}</span>
      <label htmlFor={id} className={styles.file}>
        <input id={id} type="file" name={name} className={styles.fileInput} {...rest} />
        <span className={styles.fileButton}>Выбрать файл</span>
        <span className={styles.fileName}>{fileName || hint}</span>
      </label>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
