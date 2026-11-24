import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import App from "./App";

describe("authentication", () => {
  beforeEach(() => {
    vi.stubEnv("DEV", false);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("shows a sign-in form for unauthenticated visitors", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "agentic-rag-live-memory" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("offers the account creation form on the register route", () => {
    render(
      <MemoryRouter initialEntries={["/register"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toHaveAttribute("minLength", "12");
  });

  it("opens a demo workspace directly in Vite development mode", async () => {
    vi.stubEnv("DEV", true);
    vi.spyOn(api, "demoSession").mockResolvedValue({
      access_token: "local-demo-token",
      expires_in: 1800,
      user: { id: "demo-user", email: "demo@example.test" },
    });
    vi.spyOn(api, "workspaces").mockResolvedValue([]);

    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Start with a conversation" })).toBeInTheDocument();
    expect(api.demoSession).toHaveBeenCalledOnce();
  });
});
