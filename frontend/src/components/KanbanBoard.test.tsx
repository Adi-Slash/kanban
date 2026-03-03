import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";

vi.mock("@/lib/api", () => ({
  getBoard: vi.fn().mockRejectedValue(new Error("no backend")),
  renameColumn: vi.fn(),
  addCard: vi.fn(),
  deleteCard: vi.fn(),
  moveCard: vi.fn(),
  updateCard: vi.fn(),
  setCardLabels: vi.fn(),
  aiChat: vi.fn(),
}));

const noop = () => {};

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  it("renders five columns in fallback mode", async () => {
    render(<KanbanBoard boardId="board-1" onBack={noop} />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard boardId="board-1" onBack={noop} />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard boardId="board-1" onBack={noop} />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", { name: /add card/i });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /^add$/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", { name: /delete new card/i });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("calls onBack when back button is clicked", async () => {
    const onBack = vi.fn();
    render(<KanbanBoard boardId="board-1" onBack={onBack} />);
    await screen.findAllByTestId(/column-/i);
    await userEvent.click(screen.getByLabelText("Back to boards"));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
