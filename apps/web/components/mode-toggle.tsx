import Link from "next/link";

export type ChatMode = "assistant" | "request";

type ModeToggleProps = {
  currentMode: ChatMode;
  selectedThreadId?: string;
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

export function ModeToggle({ currentMode, selectedThreadId }: ModeToggleProps) {
  return (
    <nav className="mode-toggle" aria-label="Chat mode">
      {MODE_ITEMS.map((item) => {
        const isActive = item.mode === currentMode;
        const params = new URLSearchParams();

        if (item.mode === "request") {
          params.set("mode", item.mode);
        }

        if (selectedThreadId) {
          params.set("thread", selectedThreadId);
        }

        const query = params.toString();
        const href = query ? `/chat?${query}` : "/chat";

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
