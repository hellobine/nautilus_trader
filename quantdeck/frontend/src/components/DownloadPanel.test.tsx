import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { DownloadPanel } from "./DownloadPanel";

afterEach(() => vi.restoreAllMocks());

test("creates a download job on submit", async () => {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push({ url, method: opts?.method ?? "GET" });
    if (url === "/api/downloads" && (opts?.method ?? "GET") === "POST") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({
        id: "dl-1", status: "pending", done: 0, total: 100, message: "",
        request: { market: "spot", symbol: "BTCUSDT", intervals: ["1m"], start: "2024-01-01", end: "2024-01-02" },
        created_at: "now",
      }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  }));
  render(<DownloadPanel wsFactory={() => ({ close: () => {} })} />);
  await waitFor(() => expect(screen.getByLabelText("品种")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("品种"), { target: { value: "BTCUSDT" } });
  fireEvent.change(screen.getByLabelText("开始"), { target: { value: "2024-01-01" } });
  fireEvent.change(screen.getByLabelText("结束"), { target: { value: "2024-01-02" } });
  fireEvent.click(screen.getByRole("button", { name: "开始下载" }));
  await waitFor(() => expect(screen.getByText("dl-1")).toBeInTheDocument());
});

test("updates progress from ws message", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] }));
  let handler: (m: unknown) => void = () => {};
  render(<DownloadPanel wsFactory={(_p, onMsg) => { handler = onMsg; return { close: () => {} }; }} />);
  handler({ type: "download_progress", job: {
    id: "dl-9", status: "running", done: 50, total: 100, message: "",
    request: { market: "spot", symbol: "BTCUSDT", intervals: ["1m"], start: "a", end: "b" }, created_at: "now",
  } });
  await waitFor(() => expect(screen.getByText("dl-9")).toBeInTheDocument());
  expect(screen.getByText(/50 \/ 100/)).toBeInTheDocument();
});
