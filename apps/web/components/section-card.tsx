import type { ReactNode } from "react";

type SectionCardProps = {
  eyebrow?: string;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function SectionCard({
  eyebrow,
  title,
  description,
  children,
  className,
}: SectionCardProps) {
  return (
    <section className={["section-card", className].filter(Boolean).join(" ")}>
      {(eyebrow || title || description) && (
        <header className="section-card__header">
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          {title ? <h2 className="section-card__title">{title}</h2> : null}
          {description ? <p className="section-card__description">{description}</p> : null}
        </header>
      )}
      {children}
    </section>
  );
}
