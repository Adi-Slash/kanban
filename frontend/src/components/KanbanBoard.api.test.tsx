import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  renameColumn: vi.fn(),
  addCard: vi.fn(),
  deleteCard: vi.fn(),
  moveCard: vi.fn(),
}));

import { getBoard } from "@/lib/api";

const mockedGetBoard = vi.mocked(getBoard);

describe("KanbanBoard API integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads board data from backend API", async () => {
    mockedGetBoard.mockResolvedValue(initialData);

    render(<KanbanBoard />);

    expect(await screen.findByText("Kanban Studio")).toBeInTheDocument();
    expect(mockedGetBoard).toHaveBeenCalledTimes(1);
  });

  it("shows backend load error state", async () => {
    mockedGetBoard.mockRejectedValue(new Error("network"));

    render(<KanbanBoard />);

    expect(
      await screen.findByText(/Could not load board from backend/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
