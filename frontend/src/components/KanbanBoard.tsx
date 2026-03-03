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
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[320px] w-[320px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.18)_0%,_rgba(32,157,215,0.04)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[400px] w-[400px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.12)_0%,_rgba(117,57,145,0.03)_55%,_transparent_75%)]" />

      <main className="relative flex min-h-screen flex-col gap-5 px-5 pb-6 pt-5">
        <header className="flex items-center justify-between gap-4 rounded-2xl border border-[var(--stroke)] bg-white/80 px-6 py-4 shadow-[0_2px_12px_rgba(3,33,71,0.06)] backdrop-blur">
          <div className="flex items-center gap-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--navy-dark)]">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
              </svg>
            </div>
            <div>
              <h1 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="text-xs text-[var(--gray-text)]">
                Drag cards, rename columns, or ask AI to update your board.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isLoadingBoard && (
              <span className="text-xs font-medium text-[var(--gray-text)]">Loading...</span>
            )}
            {isSaving && (
              <span className="flex items-center gap-1.5 text-xs font-medium text-[var(--primary-blue)]">
                <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2v4m0 12v4m-7.07-3.93 2.83-2.83m8.48-8.48 2.83-2.83M2 12h4m12 0h4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83" /></svg>
                Saving
              </span>
            )}
            {errorMessage && (
              <div className="flex items-center gap-2">
                <span className="max-w-xs truncate text-xs font-medium text-red-600">
                  {errorMessage}
                </span>
                <button
                  type="button"
                  onClick={() => { void loadBoard(); }}
                  className="rounded-md border border-[var(--stroke)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)]"
                >
                  Retry
                </button>
              </div>
            )}
          </div>
        </header>

        <div className="grid min-h-0 flex-1 gap-5 xl:grid-cols-[1fr_340px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid auto-cols-fr grid-flow-col gap-4">
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
                <div className="w-[240px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside
            className="flex flex-col rounded-2xl border border-[var(--stroke)] bg-white/90 p-4 shadow-[0_2px_12px_rgba(3,33,71,0.06)]"
            aria-label="AI assistant sidebar"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--secondary-purple)]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a4 4 0 0 1 4 4c0 1.95-1.4 3.57-3.25 3.92L12 22" />
                  <path d="M12 2a4 4 0 0 0-4 4c0 1.95 1.4 3.57 3.25 3.92" />
                  <path d="M8 14h8" />
                  <path d="M9 18h6" />
                </svg>
              </div>
              <div>
                <h2 className="font-display text-sm font-semibold text-[var(--navy-dark)]">
                  AI Assistant
                </h2>
                <p className="text-xs text-[var(--gray-text)]">
                  Create, move, or edit cards with AI
                </p>
              </div>
            </div>

            <div
              className="mt-4 flex-1 space-y-2 overflow-y-auto rounded-xl border border-[var(--stroke)] bg-[var(--surface)] p-3"
              data-testid="ai-chat-history"
            >
              {chatMessages.length === 0 && (
                <p className="py-6 text-center text-xs text-[var(--gray-text)]">
                  Try: &ldquo;Move the top backlog card to Review&rdquo;
                </p>
              )}
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-xl px-3 py-2 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "ml-4 bg-[var(--primary-blue)] text-white"
                      : "mr-4 border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
                  }`}
                >
                  <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider opacity-70">
                    {message.role}
                  </p>
                  <p>{message.content}</p>
                </div>
              ))}
            </div>

            {chatError && (
              <p className="mt-2 text-xs font-medium text-red-600">
                {chatError}
              </p>
            )}

            <div className="mt-3">
              <textarea
                id="ai-chat-input"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Ask AI to update your board..."
                className="h-20 w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
              <button
                type="button"
                onClick={() => { void handleSendChat(); }}
                disabled={!canSendChat}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-full bg-[var(--secondary-purple)] px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                {isChatSending ? "Sending..." : "Send"}
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};
