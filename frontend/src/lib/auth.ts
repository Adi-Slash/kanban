import { checkAuth, login as apiLogin, logout as apiLogout } from "./api";

const AUTH_COOKIE_NAME = "pm_auth";
const AUTH_COOKIE_VALUE = "1";

export const validateCredentials = async (username: string, password: string): Promise<boolean> => {
  if (username === "user" && password === "password") {
    try {
      await apiLogin(username, password);
      return true;
    } catch {
      return false;
    }
  }
  return false;
};

export const readAuthCookie = (): boolean => {
  if (typeof document === "undefined") {
    return false;
  }

  return document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .some((entry) => entry === `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}`);
};

export const writeAuthCookie = async (isAuthenticated: boolean): Promise<void> => {
  if (isAuthenticated) {
    if (typeof document !== "undefined") {
      document.cookie = `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}; Path=/; Max-Age=86400; SameSite=Lax`;
    }
    return;
  }

  try {
    await apiLogout();
  } catch {
  }

  if (typeof document !== "undefined") {
    document.cookie = `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
  }
};

export const verifyAuth = async (): Promise<boolean> => {
  return checkAuth();
};
