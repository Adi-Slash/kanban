import type { BoardData } from "@/lib/kanban";

type ApiErrorPayload = {
  detail?: string;
};

const requestBoard = async (
  path: string,
  options?: RequestInit
): Promise<BoardData> => {
  const response = await fetch(path, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (response.status === 401) {
    window.location.href = "/?unauthorized=true";
    throw new Error("Not authenticated");
  }

  if (!response.ok) {
    let detail = "";
    try {
      const errorPayload = (await response.json()) as ApiErrorPayload;
      detail = errorPayload.detail ?? "";
    } catch {
      detail = "";
    }
    const suffix = detail ? `: ${detail}` : "";
    throw new Error(`API request failed with status ${response.status}${suffix}`);
  }

  return (await response.json()) as BoardData;
};

export const getBoard = async (): Promise<BoardData> => requestBoard("/api/board");

export const login = async (username: string, password: string): Promise<void> => {
  const params = new URLSearchParams({ username, password });
  const response = await fetch(`/api/auth/login?${params}`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Login failed");
  }
};

export const logout = async (): Promise<void> => {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Logout failed");
  }
};

export const checkAuth = async (): Promise<boolean> => {
  try {
    const response = await fetch("/api/auth/status", {
      credentials: "include",
    });
    if (!response.ok) {
      return false;
    }
    const data = await response.json();
    return data.authenticated === true;
  } catch {
    return false;
  }
};

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

export type AIChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AIChatOperation = {
  type:
    | "create_card"
    | "update_card"
    | "move_card"
    | "delete_card"
    | "rename_column";
  column_id: string | null;
  card_id: string | null;
  title: string | null;
  details: string | null;
  before_card_id: string | null;
};

export type AIChatResponse = {
  assistantMessage: string;
  operations: AIChatOperation[];
  board: BoardData;
};

export const aiChat = async (
  message: string,
  history: AIChatHistoryMessage[]
): Promise<AIChatResponse> => {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      history,
    }),
  });

  if (!response.ok) {
    let detail = "";
    try {
      const errorPayload = (await response.json()) as ApiErrorPayload;
      detail = errorPayload.detail ?? "";
    } catch {
      detail = "";
    }
    const suffix = detail ? `: ${detail}` : "";
    throw new Error(`AI request failed with status ${response.status}${suffix}`);
  }

  return (await response.json()) as AIChatResponse;
};
