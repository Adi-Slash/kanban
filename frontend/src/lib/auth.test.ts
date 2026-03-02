import { readAuthCookie, validateCredentials, writeAuthCookie } from "@/lib/auth";

describe("auth", () => {
  beforeEach(() => {
    document.cookie = "pm_auth=; Path=/; Max-Age=0";
  });

  it("validates hardcoded demo credentials", () => {
    expect(validateCredentials("user", "password")).toBe(true);
    expect(validateCredentials("user", "wrong")).toBe(false);
    expect(validateCredentials("wrong", "password")).toBe(false);
  });

  it("writes and clears auth cookie", () => {
    writeAuthCookie(true);
    expect(readAuthCookie()).toBe(true);

    writeAuthCookie(false);
    expect(readAuthCookie()).toBe(false);
  });
});
