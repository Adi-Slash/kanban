"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import {
  addCard as addCardApi,
  aiChat as aiChatApi,
  deleteCard as deleteCardApi,
  getBoard,
  moveCard as moveCardApi,
  renameColumn as renameColumnApi,
  type AIChatHistoryMessage,
} from "@/lib/api";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const MAX_CHAT_MESSAGES = 20;

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData>(() => initialData);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [isLoadingBoard, setIsLoadingBoard] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatSending, setIsChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    setIsLoadingBoard(true);
    setErrorMessage(null);
    try {
      const remoteBoard = await getBoard();
      setBoard(remoteBoard);
      setIsBackendConnected(true);
    } catch {
      setIsBackendConnected(false);
      setErrorMessage(
        "Could not load board from backend. Using local fallback data for now."
      );
    } finally {
      setIsLoadingBoard(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const runLoad = async () => {
      try {
        if (!isMounted) {
          return;
        }
        await loadBoard();
      } catch {
        // handled inside loadBoard
      }
    };

    void runLoad();
    return () => {
      isMounted = false;
    };
  }, [loadBoard]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board.cards, [board.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    const activeId = active.id as string;
    const overId = over.id as string;

    if (isBackendConnected) {
      const targetColumnId = overId.startsWith("col-")
        ? overId
        : board.columns.find((column) => column.cardIds.includes(overId))?.id;
      if (!targetColumnId) {
        return;
      }
      const beforeCardId = overId.startsWith("card-") ? overId : null;
      void moveCardApi(activeId, targetColumnId, beforeCardId)
        .then((nextBoard) => {
          setBoard(nextBoard);
          setErrorMessage(null);
        })
        .catch(() => {
          setErrorMessage("Could not save card movement. Please try again.");
        })
        .finally(() => {
          setIsSaving(false);
        });
      setIsSaving(true);
      return;
    }

    setBoard((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, activeId, overId),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));

    if (!isBackendConnected) {
      return;
    }

    void renameColumnApi(columnId, title)
      .then((nextBoard) => {
        setBoard(nextBoard);
        setErrorMessage(null);
      })
      .catch(() => {
        setErrorMessage("Could not save column rename. Please try again.");
      })
      .finally(() => {
        setIsSaving(false);
      });
    setIsSaving(true);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (isBackendConnected) {
      setIsSaving(true);
      void addCardApi(columnId, title, details)
        .then((nextBoard) => {
          setBoard(nextBoard);
          setErrorMessage(null);
        })
        .catch(() => {
          setErrorMessage("Could not save new card. Please try again.");
        })
        .finally(() => {
          setIsSaving(false);
        });
      return;
    }

    const id = createId("card");
    setBoard((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (isBackendConnected) {
      setIsSaving(true);
      void deleteCardApi(columnId, cardId)
        .then((nextBoard) => {
          setBoard(nextBoard);
          setErrorMessage(null);
        })
        .catch(() => {
          setErrorMessage("Could not delete card. Please try again.");
        })
        .finally(() => {
          setIsSaving(false);
        });
      return;
    }

    setBoard((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const canSendChat = chatInput.trim().length > 0 && !isChatSending;

  const limitChatMessages = (messages: ChatMessage[]): ChatMessage[] => {
    if (messages.length <= MAX_CHAT_MESSAGES) {
      return messages;
    }
    return messages.slice(messages.length - MAX_CHAT_MESSAGES);
  };

  const handleSendChat = async () => {
    const message = chatInput.trim();
    if (!message || isChatSending) {
      return;
    }

    const userEntry: ChatMessage = {
      id: createId("chat"),
      role: "user",
      content: message,
    };
    const historyForApi: AIChatHistoryMessage[] = chatMessages.map((entry) => ({
      role: entry.role,
      content: entry.content,
    }));

    setChatInput("");
    setChatError(null);
    setIsChatSending(true);
    setChatMessages((prev) => limitChatMessages([...prev, userEntry]));

    try {
      const response = await aiChatApi(message, historyForApi);
      setBoard(response.board);
      setIsBackendConnected(true);
      setErrorMessage(null);
      setChatMessages((prev) =>
        limitChatMessages([
          ...prev,
          {
            id: createId("chat"),
            role: "assistant",
            content: response.assistantMessage,
          },
        ])
      );
    } catch (error) {
      const messageText =
        error instanceof Error
          ? error.message
          : "Could not reach AI assistant. Please try again.";
      setChatError(messageText);
    } finally {
      setIsChatSending(false);
    }
  };

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {isLoadingBoard ? (
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                Loading board...
              </p>
            ) : null}
            {isSaving ? (
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
                Saving...
              </p>
            ) : null}
            {errorMessage ? (
              <div className="flex items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-red-700">
                  {errorMessage}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    void loadBoard();
                  }}
                  className="rounded-full border border-[var(--stroke)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
                >
                  Retry
                </button>
              </div>
            ) : null}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside
            className="flex h-[720px] flex-col rounded-[28px] border border-[var(--stroke)] bg-white/90 p-5 shadow-[var(--shadow)]"
            aria-label="AI assistant sidebar"
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                AI Assistant
              </p>
              <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
                Plan board updates
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
                Ask to create, edit, move, or delete cards. Board changes refresh automatically.
              </p>
            </div>

            <div
              className="mt-5 flex-1 space-y-3 overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3"
              data-testid="ai-chat-history"
            >
              {chatMessages.length === 0 ? (
                <p className="text-sm text-[var(--gray-text)]">
                  Start by asking something like "Move the top backlog card to Review."
                </p>
              ) : null}
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-2xl px-3 py-2 text-sm leading-6 ${
                    message.role === "user"
                      ? "ml-6 bg-[var(--primary-blue)] text-white"
                      : "mr-6 border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
                  }`}
                >
                  <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.2em] opacity-80">
                    {message.role}
                  </p>
                  <p>{message.content}</p>
                </div>
              ))}
            </div>

            {chatError ? (
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-red-700">
                {chatError}
              </p>
            ) : null}

            <div className="mt-4">
              <label
                htmlFor="ai-chat-input"
                className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Ask AI
              </label>
              <textarea
                id="ai-chat-input"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Example: Rename Backlog to Ideas and add a card for interview notes."
                className="h-24 w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <button
                type="button"
                onClick={() => {
                  void handleSendChat();
                }}
                disabled={!canSendChat}
                className="mt-3 w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isChatSending ? "Sending..." : "Send to AI"}
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};
