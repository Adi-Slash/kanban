"use client";

import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardList } from "@/components/BoardList";
import { validateCredentials, registerUser, performLogout, verifyAuth } from "@/lib/auth";

type AppView = "login" | "register" | "boards" | "board";

export const KanbanApp = () => {
  const searchParams = useSearchParams();
  const [view, setView] = useState<AppView>("login");
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState("");

  const [regUsername, setRegUsername] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regDisplayName, setRegDisplayName] = useState("");
  const [regError, setRegError] = useState("");

  useEffect(() => {
    const checkAuth = async () => {
      const isAuth = await verifyAuth();
      if (isAuth) {
        setView("boards");
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  useEffect(() => {
    if (searchParams && searchParams.get("unauthorized") === "true") {
      setView("login");
      setLoginError("Session expired. Please log in again.");
    }
  }, [searchParams]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError("");
    const isValid = await validateCredentials(loginUsername, loginPassword);
    if (!isValid) {
      setLoginError("Invalid credentials.");
      return;
    }
    setLoginPassword("");
    setView("boards");
  };

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRegError("");
    const success = await registerUser(regUsername, regPassword, regDisplayName);
    if (!success) {
      setRegError("Registration failed. Username may already be taken.");
      return;
    }
    setRegPassword("");
    setView("boards");
  };

  const handleLogout = async () => {
    await performLogout();
    setView("login");
    setLoginUsername("");
    setLoginPassword("");
    setLoginError("");
    setSelectedBoardId(null);
  };

  const handleSelectBoard = (boardId: string) => {
    setSelectedBoardId(boardId);
    setView("board");
  };

  const handleBackToBoards = () => {
    setSelectedBoardId(null);
    setView("boards");
  };

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center px-6 py-12">
        <p className="text-sm text-[var(--gray-text)]">Loading...</p>
      </main>
    );
  }

  if (view === "register") {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center px-6 py-12">
        <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Project Management
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Create Account
          </h1>
          <form className="mt-6 space-y-4" onSubmit={handleRegister}>
            <div>
              <label
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="reg-username"
              >
                Username
              </label>
              <input
                id="reg-username"
                value={regUsername}
                onChange={(e) => setRegUsername(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                autoComplete="username"
                required
                minLength={2}
              />
            </div>
            <div>
              <label
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="reg-displayname"
              >
                Display Name (optional)
              </label>
              <input
                id="reg-displayname"
                value={regDisplayName}
                onChange={(e) => setRegDisplayName(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              />
            </div>
            <div>
              <label
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="reg-password"
              >
                Password
              </label>
              <input
                id="reg-password"
                type="password"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                autoComplete="new-password"
                required
                minLength={4}
              />
            </div>
            {regError ? (
              <p className="text-sm font-medium text-red-700" role="alert">
                {regError}
              </p>
            ) : null}
            <button
              type="submit"
              className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110"
            >
              Create Account
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-[var(--gray-text)]">
            Already have an account?{" "}
            <button
              type="button"
              onClick={() => { setView("login"); setRegError(""); }}
              className="font-semibold text-[var(--primary-blue)] hover:underline"
            >
              Sign in
            </button>
          </p>
        </section>
      </main>
    );
  }

  if (view === "login") {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center px-6 py-12">
        <section className="w-full rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Project Management
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Sign in
          </h1>
          <p className="mt-3 text-sm text-[var(--gray-text)]">
            Sign in to access your boards. Demo: user / password
          </p>
          <form className="mt-6 space-y-4" onSubmit={handleLogin}>
            <div>
              <label
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="username"
              >
                Username
              </label>
              <input
                id="username"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                autoComplete="username"
                required
              />
            </div>
            <div>
              <label
                className="mb-1 block text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="password"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                autoComplete="current-password"
                required
              />
            </div>
            {loginError ? (
              <p className="text-sm font-medium text-red-700" role="alert">
                {loginError}
              </p>
            ) : null}
            <button
              type="submit"
              className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110"
            >
              Sign in
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-[var(--gray-text)]">
            New here?{" "}
            <button
              type="button"
              onClick={() => { setView("register"); setLoginError(""); }}
              className="font-semibold text-[var(--primary-blue)] hover:underline"
            >
              Create an account
            </button>
          </p>
        </section>
      </main>
    );
  }

  if (view === "boards") {
    return (
      <BoardList
        onSelectBoard={handleSelectBoard}
        onLogout={() => { void handleLogout(); }}
      />
    );
  }

  if (view === "board" && selectedBoardId) {
    return (
      <KanbanBoard boardId={selectedBoardId} onBack={handleBackToBoards} />
    );
  }

  return null;
};
