import { validateCredentials, registerUser, verifyAuth } from "@/lib/auth";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual("@/lib/api");
  return {
    ...actual,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    register: vi.fn().mockResolvedValue(undefined),
    checkAuth: vi.fn().mockResolvedValue(true),
  };
});

describe("auth", () => {
  it("validates credentials by calling API login", async () => {
    const result = await validateCredentials("user", "password");
    expect(result).toBe(true);
  });

  it("returns false when API login rejects", async () => {
    const { login } = await import("@/lib/api");
    vi.mocked(login).mockRejectedValueOnce(new Error("401"));
    const result = await validateCredentials("user", "wrong");
    expect(result).toBe(false);
  });

  it("registers a new user", async () => {
    const result = await registerUser("alice", "pass1234", "Alice");
    expect(result).toBe(true);
  });

  it("returns false when registration fails", async () => {
    const { register } = await import("@/lib/api");
    vi.mocked(register).mockRejectedValueOnce(new Error("409"));
    const result = await registerUser("user", "pass", "");
    expect(result).toBe(false);
  });

  it("verifies auth status", async () => {
    const result = await verifyAuth();
    expect(result).toBe(true);
  });
});
