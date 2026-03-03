import { checkAuth, readAuthCookie, validateCredentials, writeAuthCookie } from "@/lib/auth";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual("@/lib/api");
  return {
    ...actual,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    checkAuth: vi.fn().mockResolvedValue(true),
  };
});

describe("auth", () => {
  beforeEach(() => {
    document.cookie = "pm_auth=; Path=/; Max-Age=0";
  });

  it("validates hardcoded demo credentials", async () => {
    const result = await validateCredentials("user", "password");
    expect(result).toBe(true);
    expect(validateCredentials("user", "wrong")).resolves.toBe(false);
    expect(validateCredentials("wrong", "password")).resolves.toBe(false);
  });

  it("writes and clears auth cookie", async () => {
    await writeAuthCookie(true);
    expect(readAuthCookie()).toBe(true);

    await writeAuthCookie(false);
    expect(readAuthCookie()).toBe(false);
  });
});
