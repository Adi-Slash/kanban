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
    checkAuth: vi.fn().mockResolvedValue(false),
  };
});

describe("KanbanApp auth flow", () => {
  beforeEach(() => {
    document.cookie = "pm_auth=; Path=/; Max-Age=0";
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
    expect(
      screen.queryByRole("heading", { name: "Kanban Studio" })
    ).not.toBeInTheDocument();
  });

  it("shows an error for invalid credentials", async () => {
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

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid credentials. Use user / password."
    );
  });

  it("logs in and logs out successfully", async () => {
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
      expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });
  });
});
