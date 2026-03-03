"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Label } from "@/lib/kanban";
import { priorityColors } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  boardLabels: Label[];
  onDelete: (cardId: string) => void;
  onOpenDetail: (cardId: string) => void;
};

export const KanbanCard = ({
  card,
  boardLabels,
  onDelete,
  onOpenDetail,
}: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const cardLabels = boardLabels.filter((l) => card.labelIds.includes(l.id));
  const isOverdue =
    card.dueDate && new Date(card.dueDate) < new Date(new Date().toISOString().split("T")[0]);

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative rounded-2xl border border-transparent bg-white px-4 py-3 shadow-[0_2px_8px_rgba(3,33,71,0.06)]",
        "transition-all duration-150",
        "hover:shadow-[0_6px_16px_rgba(3,33,71,0.10)]",
        isDragging && "opacity-60 shadow-[0_12px_24px_rgba(3,33,71,0.14)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      {cardLabels.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {cardLabels.map((label) => (
            <span
              key={label.id}
              className="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold text-white"
              style={{ backgroundColor: label.color }}
            >
              {label.name}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-start justify-between gap-2">
        <button
          type="button"
          onClick={() => onOpenDetail(card.id)}
          className="min-w-0 flex-1 text-left"
        >
          <h4 className="font-display text-sm font-semibold leading-snug text-[var(--navy-dark)]">
            {card.title}
          </h4>
          {card.details && (
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-[var(--gray-text)]">
              {card.details}
            </p>
          )}
        </button>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[var(--gray-text)] opacity-0 transition hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
          aria-label={`Delete ${card.title}`}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 6h18" />
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
        </button>
      </div>

      <div className="mt-2 flex items-center gap-2">
        {card.priority !== "medium" && (
          <span
            className="inline-flex rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase text-white"
            style={{ backgroundColor: priorityColors[card.priority] }}
          >
            {card.priority}
          </span>
        )}
        {card.dueDate && (
          <span
            className={clsx(
              "text-[10px] font-medium",
              isOverdue ? "text-red-500" : "text-[var(--gray-text)]"
            )}
          >
            {card.dueDate}
          </span>
        )}
      </div>
    </article>
  );
};
