import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanApp } from "@/components/KanbanApp";

describe("KanbanApp auth flow", () => {
  beforeEach(() => {
    document.cookie = "pm_auth=; Path=/; Max-Age=0";
  });

  it("shows login form for unauthenticated users", () => {
    render(<KanbanApp />);

    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Kanban Studio" })
    ).not.toBeInTheDocument();
  });

  it("shows an error for invalid credentials", async () => {
    render(<KanbanApp />);

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "nope");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Invalid credentials. Use user / password."
    );
  });

  it("logs in and logs out successfully", async () => {
    render(<KanbanApp />);

    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });
});
