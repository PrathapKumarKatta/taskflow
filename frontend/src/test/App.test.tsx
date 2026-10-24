import { it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";
import { session } from "../api";

it("requests bounded server pages and sends filters to the API", async () => {
  session.set("test-token");
  const requested: URL[] = [];
  const created_at = "2026-10-24T00:00:00Z";
  vi.stubGlobal("fetch", vi.fn(async (input: string) => {
    const url = new URL(input, "http://localhost");
    requested.push(url);
    const path = url.pathname;
    let body: unknown;
    if (path === "/api/v1/users/me") body = { id: "user", full_name: "Owner", email: "owner@example.com", created_at };
    else if (path.endsWith("/members")) body = [{ user_id: "user", workspace_id: "workspace", role: "owner", joined_at: created_at }];
    else if (path.endsWith("/projects")) body = { items: [{ id: "project", workspace_id: "workspace", name: "Test project", created_at }], total: 1 };
    else if (path.endsWith("/workspaces")) body = { items: [{ id: "workspace", name: "Test workspace", owner_id: "user", created_at }], total: 1 };
    else if (path.endsWith("/stats")) body = { total: 81, by_status: { todo: 81, in_progress: 0, blocked: 0, done: 0 }, overdue: 0, my_open: 81 };
    else if (path.endsWith("/tasks")) {
      const offset = Number(url.searchParams.get("offset"));
      const limit = Number(url.searchParams.get("limit"));
      body = {
        items: Array.from({ length: Math.min(limit, 81 - offset) }, (_, i) => ({
          id: `task-${offset + i}`, project_id: "project", workspace_id: "workspace",
          title: `Task ${offset + i}`, description: "", status: "todo", priority: "medium",
          creator_id: "user", assignee_id: "user", due_at: null, version: 1,
          created_at, updated_at: created_at,
        })), total: 81, limit, offset,
      };
    } else body = { status: "ready" };
    return Response.json(body);
  }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });
  render(<QueryClientProvider client={qc}><App /></QueryClientProvider>);
  await screen.findByText("Task 0");
  expect(requested.filter(u => u.pathname.endsWith("/tasks"))).toHaveLength(1);
  expect(screen.queryByText("Task 40")).toBeNull();
  const actions = userEvent.setup();
  await actions.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Task 40");
  await actions.click(screen.getByRole("button", { name: "List" }));
  await screen.findByText("Task 0");
  await actions.click(screen.getByRole("button", { name: "Next page" }));
  await screen.findByText("Task 10");
  expect(requested.some(u => u.searchParams.get("limit") === "10" && u.searchParams.get("offset") === "10")).toBe(true);
  await actions.type(screen.getByRole("textbox", { name: "Search tasks" }), "specific task");
  await waitFor(() => expect(requested.some(u => u.searchParams.get("q") === "specific task" && u.searchParams.get("offset") === "0")).toBe(true));
  expect(requested.filter(u => u.pathname.endsWith("/tasks")).every(u => Number(u.searchParams.get("limit")) <= 40)).toBe(true);
});
