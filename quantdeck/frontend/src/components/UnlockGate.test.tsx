import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { UnlockGate } from "./UnlockGate";

afterEach(() => vi.restoreAllMocks());

test("shows children when unlocked", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200, json: async () => ({ unlocked: true, initialized: true }),
  }));
  render(<UnlockGate><div>内部内容</div></UnlockGate>);
  await waitFor(() => expect(screen.getByText("内部内容")).toBeInTheDocument());
});

test("shows passphrase form when locked, unlocks on submit", async () => {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push(`${opts?.method ?? "GET"} ${url}`);
    if (url === "/api/lock-status") {
      const unlocked = calls.filter((c) => c === "POST /api/unlock").length > 0;
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked, initialized: true }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked: true }) });
  }));
  render(<UnlockGate><div>内部内容</div></UnlockGate>);
  await waitFor(() => expect(screen.getByLabelText("主口令")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("主口令"), { target: { value: "pw" } });
  fireEvent.click(screen.getByRole("button", { name: "解锁" }));
  await waitFor(() => expect(screen.getByText("内部内容")).toBeInTheDocument());
});
