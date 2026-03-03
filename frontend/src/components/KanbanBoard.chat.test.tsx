import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn(),
  renameColumn: vi.fn(),
  addCard: vi.fn(),
  deleteCard: vi.fn(),
  moveCard: vi.fn(),
  aiChat: vi.fn(),
}));

import { aiChat, getBoard } from "@/lib/api";

const mockedGetBoard = vi.mocked(getBoard);
const mockedAiChat = vi.mocked(aiChat);

const withAddedCard = (): BoardData => {
  const cardId = "card-999";
  return {
    ...initialData,
    columns: initialData.columns.map((column, index) =>
      index === 0 ? { ...column, cardIds: [...column.cardIds, cardId] } : column
    ),
    cards: {
      ...initialData.cards,
      [cardId]: {
        id: cardId,
        title: "AI Card",
        details: "Created from chat",
      },
    },
  };
};

describe("KanbanBoard AI chat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetBoard.mockResolvedValue(initialData);
  });

  it("sends user message and refreshes board from AI response", async () => {
    mockedAiChat.mockResolvedValue({
      assistantMessage: "Added a new card in Backlog.",
      operations: [
        {
          type: "create_card",
          column_id: initialData.columns[0].id,
          card_id: null,
          title: "AI Card",
          details: "Created from chat",
          before_card_id: null,
        },
      ],
      board: withAddedCard(),
    });

    render(<KanbanBoard />);

    await screen.findByText("Kanban Studio");
    await userEvent.type(
      screen.getByPlaceholderText(/ask ai/i),
      "Add a card called AI Card in Backlog"
    );
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Added a new card in Backlog.")).toBeInTheDocument();
    expect(mockedAiChat).toHaveBeenCalledWith("Add a card called AI Card in Backlog", []);

    const firstColumn = screen.getAllByTestId(/column-/i)[0];
    expect(within(firstColumn).getByText("AI Card")).toBeInTheDocument();
  });

  it("shows inline AI error on chat failure", async () => {
    mockedAiChat.mockRejectedValue(new Error("AI request failed with status 502"));

    render(<KanbanBoard />);

    await screen.findByText("Kanban Studio");
    await userEvent.type(screen.getByPlaceholderText(/ask ai/i), "Move card-1 to Review");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByText(/AI request failed with status 502/i)
    ).toBeInTheDocument();
  });
});
