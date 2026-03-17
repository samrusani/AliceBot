import Link from "next/link";

export type ChatMode = "assistant" | "request";

type ModeToggleProps = {
  currentMode: ChatMode;
};

const MODE_ITEMS: Array<{
  mode: ChatMode;
  label: string;
  description: string;
}> = [
  {
    mode: "assistant",
    label: "Ask the assistant",
    description: "Normal ask-and-answer interaction through the shipped response seam.",
  },
  {
    mode: "request",
    label: "Submit a governed request",
    description: "Approval-gated action submission through the existing request seam.",
  },
];

export function ModeToggle({ currentMode }: ModeToggleProps) {
  return (
    <nav className="mode-toggle" aria-label="Chat mode">
      {MODE_ITEMS.map((item) => {
        const isActive = item.mode === currentMode;
        const href = item.mode === "assistant" ? "/chat" : `/chat?mode=${item.mode}`;

        return (
          <Link
            key={item.mode}
            href={href}
            className={["mode-toggle__item", isActive ? "is-active" : ""].filter(Boolean).join(" ")}
            aria-current={isActive ? "page" : undefined}
          >
            <span className="mode-toggle__label">{item.label}</span>
            <span className="mode-toggle__description">{item.description}</span>
          </Link>
        );
      })}
    </nav>
  );
}
