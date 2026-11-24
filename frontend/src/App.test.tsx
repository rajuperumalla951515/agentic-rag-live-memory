import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("authentication", () => {
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
});
