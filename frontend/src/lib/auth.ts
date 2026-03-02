const AUTH_COOKIE_NAME = "pm_auth";
const AUTH_COOKIE_VALUE = "1";

export const validateCredentials = (username: string, password: string): boolean =>
  username === "user" && password === "password";

export const readAuthCookie = (): boolean => {
  if (typeof document === "undefined") {
    return false;
  }

  return document.cookie
    .split(";")
    .map((entry) => entry.trim())
    .some((entry) => entry === `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}`);
};

export const writeAuthCookie = (isAuthenticated: boolean): void => {
  if (typeof document === "undefined") {
    return;
  }

  if (isAuthenticated) {
    document.cookie = `${AUTH_COOKIE_NAME}=${AUTH_COOKIE_VALUE}; Path=/; Max-Age=86400; SameSite=Lax`;
    return;
  }

  document.cookie = `${AUTH_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
};
