import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanApp } from "@/components/KanbanApp";
import { Suspense } from "react";
import * as nextNavigation from "next/navigation";

vi.mock("next/navigation", () => ({
  useSearchParams: vi.fn(() => new URLSearchParams()),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual("@/lib/api");
  return {
    ...actual,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    register: vi.fn().mockResolvedValue(undefined),
    checkAuth: vi.fn().mockResolvedValue(false),
    listBoards: vi.fn().mockResolvedValue([
      { id: "board-1", name: "My Board", description: "", columnCount: 5, cardCount: 8, updatedAt: "2026-01-01" },
    ]),
    getBoard: vi.fn().mockResolvedValue({
      id: "board-1",
      name: "My Board",
      description: "",
      columns: [{ id: "col-1", title: "Backlog", cardIds: [] }],
      cards: {},
      labels: [],
    }),
  };
});

describe("KanbanApp auth flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (nextNavigation.useSearchParams as ReturnType<typeof vi.fn>).mockReturnValue(
      new URLSearchParams()
    );
  });

  it("shows login form for unauthenticated users", async () => {
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <KanbanApp />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("shows register form when Create an account is clicked", async () => {
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <KanbanApp />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Create an account"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Create Account" })).toBeInTheDocument();
    });
  });

  it("shows error for invalid credentials", async () => {
    const { login } = await import("@/lib/api");
    vi.mocked(login).mockRejectedValueOnce(new Error("401"));

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <KanbanApp />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid credentials");
  });

  it("navigates to board list after login", async () => {
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <KanbanApp />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Your Boards" })).toBeInTheDocument();
    });
  });

  it("logs out from board list", async () => {
    render(
      <Suspense fallback={<div>Loading...</div>}>
        <KanbanApp />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Your Boards" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Log out" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });
});
