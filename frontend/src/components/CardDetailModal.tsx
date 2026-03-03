"use client";

import { useState } from "react";
import type { Card, Label } from "@/lib/kanban";
import { priorityColors } from "@/lib/kanban";

type CardDetailModalProps = {
  card: Card;
  labels: Label[];
  onClose: () => void;
  onUpdate: (data: {
    title?: string;
    details?: string;
    priority?: string;
    dueDate?: string | null;
  }) => void;
  onSetLabels: (labelIds: string[]) => void;
  onDelete: () => void;
};

export const CardDetailModal = ({
  card,
  labels,
  onClose,
  onUpdate,
  onSetLabels,
  onDelete,
}: CardDetailModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [priority, setPriority] = useState(card.priority);
  const [dueDate, setDueDate] = useState(card.dueDate ?? "");
  const [selectedLabelIds, setSelectedLabelIds] = useState<string[]>(
    card.labelIds
  );
  const [isDirty, setIsDirty] = useState(false);

  const handleSave = () => {
    const updates: Record<string, string | null | undefined> = {};
    if (title !== card.title) updates.title = title;
    if (details !== card.details) updates.details = details;
    if (priority !== card.priority) updates.priority = priority;
    if (dueDate !== (card.dueDate ?? "")) {
      updates.dueDate = dueDate || null;
    }
    if (Object.keys(updates).length > 0) {
      onUpdate(updates);
    }
    const labelsChanged =
      selectedLabelIds.length !== card.labelIds.length ||
      selectedLabelIds.some((id) => !card.labelIds.includes(id));
    if (labelsChanged) {
      onSetLabels(selectedLabelIds);
    }
    onClose();
  };

  const markDirty = () => setIsDirty(true);

  const toggleLabel = (labelId: string) => {
    markDirty();
    setSelectedLabelIds((prev) =>
      prev.includes(labelId)
        ? prev.filter((id) => id !== labelId)
        : [...prev, labelId]
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Edit Card
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Title
            </label>
            <input
              value={title}
              onChange={(e) => { setTitle(e.target.value); markDirty(); }}
              className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              Details
            </label>
            <textarea
              value={details}
              onChange={(e) => { setDetails(e.target.value); markDirty(); }}
              rows={3}
              className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => {
                  setPriority(e.target.value as Card["priority"]);
                  markDirty();
                }}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              >
                {(["low", "medium", "high", "urgent"] as const).map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Due Date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => { setDueDate(e.target.value); markDirty(); }}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
            </div>
          </div>

          {labels.length > 0 && (
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Labels
              </label>
              <div className="flex flex-wrap gap-2">
                {labels.map((label) => {
                  const isSelected = selectedLabelIds.includes(label.id);
                  return (
                    <button
                      key={label.id}
                      type="button"
                      onClick={() => toggleLabel(label.id)}
                      className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition"
                      style={{
                        borderColor: isSelected ? label.color : "var(--stroke)",
                        backgroundColor: isSelected ? label.color + "18" : "transparent",
                        color: isSelected ? label.color : "var(--gray-text)",
                      }}
                    >
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: label.color }}
                      />
                      {label.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {card.priority !== "medium" || card.dueDate ? (
            <div className="flex items-center gap-3 text-xs">
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium text-white"
                style={{ backgroundColor: priorityColors[card.priority] }}
              >
                {card.priority}
              </span>
              {card.dueDate && (
                <span className="text-[var(--gray-text)]">
                  Due: {card.dueDate}
                </span>
              )}
            </div>
          ) : null}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <button
            type="button"
            onClick={onDelete}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold text-red-500 transition hover:bg-red-50"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18" />
              <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
            </svg>
            Delete Card
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!isDirty}
              className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition enabled:hover:brightness-110 disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
