import {
  checkAuth,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
} from "./api";

export const validateCredentials = async (
  username: string,
  password: string
): Promise<boolean> => {
  try {
    await apiLogin(username, password);
    return true;
  } catch {
    return false;
  }
};

export const registerUser = async (
  username: string,
  password: string,
  displayName: string
): Promise<boolean> => {
  try {
    await apiRegister(username, password, displayName);
    return true;
  } catch {
    return false;
  }
};

export const performLogout = async (): Promise<void> => {
  try {
    await apiLogout();
  } catch {
    // best-effort
  }
};

export const verifyAuth = async (): Promise<boolean> => {
  return checkAuth();
};
