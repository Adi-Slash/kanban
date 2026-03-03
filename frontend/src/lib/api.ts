import type { BoardData, BoardSummary, Label } from "@/lib/kanban";

type ApiErrorPayload = {
  detail?: string;
};

const apiFetch = async <T>(
  path: string,
  options?: RequestInit
): Promise<T> => {
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

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
};

// ---- Auth ----

export const register = async (
  username: string,
  password: string,
  displayName: string
): Promise<void> => {
  await apiFetch<{ message: string }>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password, displayName }),
  });
};

export const login = async (
  username: string,
  password: string
): Promise<void> => {
  await apiFetch<{ message: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
};

export const logout = async (): Promise<void> => {
  await apiFetch<{ message: string }>("/api/auth/logout", {
    method: "POST",
  });
};

export const checkAuth = async (): Promise<boolean> => {
  try {
    const data = await apiFetch<{ authenticated: boolean }>("/api/auth/status");
    return data.authenticated === true;
  } catch {
    return false;
  }
};

export type ProfileData = {
  username: string;
  displayName: string;
};

export const getProfile = async (): Promise<ProfileData> =>
  apiFetch<ProfileData>("/api/auth/profile");

export const updateProfile = async (
  displayName: string
): Promise<ProfileData> =>
  apiFetch<ProfileData>("/api/auth/profile", {
    method: "PATCH",
    body: JSON.stringify({ displayName }),
  });

// ---- Boards ----

export const listBoards = async (): Promise<BoardSummary[]> =>
  apiFetch<BoardSummary[]>("/api/boards");

export const createBoard = async (
  name: string,
  description: string = ""
): Promise<BoardSummary> =>
  apiFetch<BoardSummary>("/api/boards", {
    method: "POST",
    body: JSON.stringify({ name, description }),
  });

export const getBoard = async (boardId: string): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}`);

export const updateBoard = async (
  boardId: string,
  data: { name?: string; description?: string }
): Promise<BoardSummary> =>
  apiFetch<BoardSummary>(`/api/boards/${boardId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteBoard = async (boardId: string): Promise<void> =>
  apiFetch<void>(`/api/boards/${boardId}`, { method: "DELETE" });

// ---- Column operations ----

export const renameColumn = async (
  boardId: string,
  columnId: string,
  title: string
): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

// ---- Card CRUD ----

export const addCard = async (
  boardId: string,
  columnId: string,
  title: string,
  details: string,
  priority: string = "medium",
  dueDate: string | null = null
): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}/columns/${columnId}/cards`, {
    method: "POST",
    body: JSON.stringify({ title, details, priority, dueDate }),
  });

export const updateCard = async (
  boardId: string,
  cardId: string,
  data: {
    title?: string;
    details?: string;
    priority?: string;
    dueDate?: string | null;
  }
): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteCard = async (
  boardId: string,
  columnId: string,
  cardId: string
): Promise<BoardData> =>
  apiFetch<BoardData>(
    `/api/boards/${boardId}/columns/${columnId}/cards/${cardId}`,
    { method: "DELETE" }
  );

export const moveCard = async (
  boardId: string,
  cardId: string,
  targetColumnId: string,
  beforeCardId: string | null
): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}/cards/${cardId}/move`, {
    method: "POST",
    body: JSON.stringify({ targetColumnId, beforeCardId }),
  });

// ---- Labels ----

export const createLabel = async (
  boardId: string,
  name: string,
  color: string
): Promise<Label> =>
  apiFetch<Label>(`/api/boards/${boardId}/labels`, {
    method: "POST",
    body: JSON.stringify({ name, color }),
  });

export const updateLabel = async (
  boardId: string,
  labelId: string,
  data: { name?: string; color?: string }
): Promise<Label> =>
  apiFetch<Label>(`/api/boards/${boardId}/labels/${labelId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteLabel = async (
  boardId: string,
  labelId: string
): Promise<void> =>
  apiFetch<void>(`/api/boards/${boardId}/labels/${labelId}`, {
    method: "DELETE",
  });

export const setCardLabels = async (
  boardId: string,
  cardId: string,
  labelIds: string[]
): Promise<BoardData> =>
  apiFetch<BoardData>(`/api/boards/${boardId}/cards/${cardId}/labels`, {
    method: "PUT",
    body: JSON.stringify({ labelIds }),
  });

// ---- AI Chat ----

export type AIChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AIChatOperation = {
  type: "create_card" | "update_card" | "move_card" | "delete_card" | "rename_column";
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
  boardId: string,
  message: string,
  history: AIChatHistoryMessage[]
): Promise<AIChatResponse> =>
  apiFetch<AIChatResponse>(`/api/boards/${boardId}/ai/chat`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
