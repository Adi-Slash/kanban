import type { BoardData } from "@/lib/kanban";

const requestBoard = async (
  path: string,
  options?: RequestInit
): Promise<BoardData> => {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return (await response.json()) as BoardData;
};

export const getBoard = async (): Promise<BoardData> => requestBoard("/api/board");

export const renameColumn = async (
  columnId: string,
  title: string
): Promise<BoardData> =>
  requestBoard(`/api/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

export const addCard = async (
  columnId: string,
  title: string,
  details: string
): Promise<BoardData> =>
  requestBoard(`/api/columns/${columnId}/cards`, {
    method: "POST",
    body: JSON.stringify({ title, details }),
  });

export const deleteCard = async (
  columnId: string,
  cardId: string
): Promise<BoardData> =>
  requestBoard(`/api/columns/${columnId}/cards/${cardId}`, {
    method: "DELETE",
  });

export const moveCard = async (
  cardId: string,
  targetColumnId: string,
  beforeCardId: string | null
): Promise<BoardData> =>
  requestBoard(`/api/cards/${cardId}/move`, {
    method: "POST",
    body: JSON.stringify({
      targetColumnId,
      beforeCardId,
    }),
  });
