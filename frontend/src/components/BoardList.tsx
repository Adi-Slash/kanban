"use client";

import { useEffect, useState } from "react";
import type { BoardSummary } from "@/lib/kanban";
import {
  listBoards,
  createBoard as createBoardApi,
  deleteBoard as deleteBoardApi,
  updateBoard as updateBoardApi,
} from "@/lib/api";

type BoardListProps = {
  onSelectBoard: (boardId: string) => void;
  onLogout: () => void;
};

export const BoardList = ({ onSelectBoard, onLogout }: BoardListProps) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [newBoardDesc, setNewBoardDesc] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");

  const loadBoards = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listBoards();
      setBoards(data);
    } catch {
      setError("Could not load boards.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadBoards();
  }, []);

  const handleCreate = async () => {
    if (!newBoardName.trim()) return;
    try {
      await createBoardApi(newBoardName.trim(), newBoardDesc.trim());
      setNewBoardName("");
      setNewBoardDesc("");
      setShowCreateForm(false);
      await loadBoards();
    } catch {
      setError("Could not create board.");
    }
  };

  const handleDelete = async (boardId: string) => {
    try {
      await deleteBoardApi(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch {
      setError("Could not delete board.");
    }
  };

  const handleRename = async (boardId: string) => {
    if (!editName.trim()) return;
    try {
      await updateBoardApi(boardId, { name: editName.trim() });
      setEditingId(null);
      await loadBoards();
    } catch {
      setError("Could not rename board.");
    }
  };

  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute left-0 top-0 h-[320px] w-[320px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.18)_0%,_rgba(32,157,215,0.04)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[400px] w-[400px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.12)_0%,_rgba(117,57,145,0.03)_55%,_transparent_75%)]" />

      <main className="relative mx-auto max-w-4xl px-6 py-10">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
              Project Management
            </p>
            <h1 className="mt-1 font-display text-3xl font-semibold text-[var(--navy-dark)]">
              Your Boards
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowCreateForm(true)}
              className="flex items-center gap-1.5 rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:brightness-110"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              New Board
            </button>
            <button
              type="button"
              onClick={onLogout}
              className="flex items-center gap-1.5 rounded-lg border border-[var(--stroke)] bg-white px-3 py-2 text-xs font-semibold text-[var(--gray-text)] shadow-sm transition hover:text-[var(--navy-dark)]"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Log out
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {showCreateForm && (
          <div className="mt-6 rounded-2xl border border-[var(--stroke)] bg-white p-6 shadow-sm">
            <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">
              Create Board
            </h2>
            <div className="mt-4 space-y-3">
              <input
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                placeholder="Board name"
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                autoFocus
              />
              <textarea
                value={newBoardDesc}
                onChange={(e) => setNewBoardDesc(e.target.value)}
                placeholder="Description (optional)"
                rows={2}
                className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--gray-text)] outline-none focus:border-[var(--primary-blue)]"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void handleCreate()}
                  className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white transition hover:brightness-110"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewBoardName("");
                    setNewBoardDesc("");
                  }}
                  className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="mt-10 text-center text-sm text-[var(--gray-text)]">
            Loading boards...
          </p>
        ) : boards.length === 0 ? (
          <div className="mt-10 rounded-2xl border border-dashed border-[var(--stroke)] p-12 text-center">
            <p className="text-sm text-[var(--gray-text)]">
              No boards yet. Create your first board to get started.
            </p>
          </div>
        ) : (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {boards.map((board) => (
              <div
                key={board.id}
                className="group relative rounded-2xl border border-[var(--stroke)] bg-white p-5 shadow-sm transition hover:shadow-md"
              >
                {editingId === board.id ? (
                  <div className="space-y-2">
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="w-full rounded-lg border border-[var(--stroke)] bg-[var(--surface)] px-2 py-1 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void handleRename(board.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => void handleRename(board.id)}
                        className="text-xs font-semibold text-[var(--primary-blue)]"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="text-xs text-[var(--gray-text)]"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => onSelectBoard(board.id)}
                      className="block w-full text-left"
                    >
                      <h3 className="font-display text-base font-semibold text-[var(--navy-dark)]">
                        {board.name}
                      </h3>
                      {board.description && (
                        <p className="mt-1 line-clamp-2 text-xs text-[var(--gray-text)]">
                          {board.description}
                        </p>
                      )}
                      <div className="mt-3 flex gap-4 text-xs text-[var(--gray-text)]">
                        <span>{board.columnCount} columns</span>
                        <span>{board.cardCount} cards</span>
                      </div>
                    </button>
                    <div className="absolute right-3 top-3 flex gap-1 opacity-0 transition group-hover:opacity-100">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingId(board.id);
                          setEditName(board.name);
                        }}
                        className="rounded-md p-1 text-[var(--gray-text)] hover:bg-[var(--surface)] hover:text-[var(--primary-blue)]"
                        aria-label={`Rename ${board.name}`}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          void handleDelete(board.id);
                        }}
                        className="rounded-md p-1 text-[var(--gray-text)] hover:bg-red-50 hover:text-red-500"
                        aria-label={`Delete ${board.name}`}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M3 6h18" />
                          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};
