import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TaskPanel from "../TaskPanel";
import type { Task, User } from "../types";

const user: User = { id: "owner", email: "owner@example.com", full_name: "Owner", created_at: "2026-10-24T00:00:00Z" };
const task: Task = {
  id: "task", project_id: "project", workspace_id: "workspace",
  title: "Original title", description: "Original description", status: "todo",
  priority: "medium", assignee_id: null, creator_id: user.id, due_at: null,
  version: 1, created_at: user.created_at, updated_at: user.created_at,
};

describe("task edit conflict recovery", () => {
  it("preserves the draft, adopts unrelated server edits, and saves only changed fields", async () => {
    const requests: Record<string, unknown>[] = [];
    const latest = { ...task, version: 2, description: "Another member's description" };
    vi.stubGlobal("fetch", vi.fn(async (input: string, options?: RequestInit) => {
      if (options?.method === "PATCH") {
        const body = JSON.parse(String(options.body));
        requests.push(body);
        if (requests.length === 1) return Response.json({ detail: "Task changed" }, { status: 409 });
        return Response.json({ ...latest, ...body, version: 3 });
      }
      if (input.endsWith("/tasks/task")) return Response.json(latest);
      return Response.json({ items: [], total: 0, limit: 100, offset: 0 });
    }));
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={qc}><TaskPanel
      task={task} user={user} members={[]} close={vi.fn()} refresh={async () => {}}
    /></QueryClientProvider>);
    const actions = userEvent.setup();
    await actions.clear(screen.getByLabelText("Task name"));
    await actions.type(screen.getByLabelText("Task name"), "My draft title");
    await actions.click(screen.getByRole("button", { name: /save/i }));
    await actions.click(await screen.findByRole("button", { name: /load latest version/i }));
    await waitFor(() => expect((screen.getByLabelText("Description") as HTMLTextAreaElement).value).toBe(latest.description));
    expect((screen.getByLabelText("Task name") as HTMLInputElement).value).toBe("My draft title");
    await actions.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1]).toEqual({ title: "My draft title", expected_version: 2 });
  });
});
