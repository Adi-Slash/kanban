import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_12px_24px_rgba(3,33,71,0.14)]">
    <h4 className="font-display text-sm font-semibold leading-snug text-[var(--navy-dark)]">
      {card.title}
    </h4>
    {card.details && (
      <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--gray-text)]">
        {card.details}
      </p>
    )}
  </article>
);
