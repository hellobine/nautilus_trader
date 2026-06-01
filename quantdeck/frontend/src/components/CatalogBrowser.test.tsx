import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CatalogBrowser } from "./CatalogBrowser";

afterEach(() => vi.restoreAllMocks());

test("renders catalog entries", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => [
      { instrument_id: "BTCUSDT.BINANCE", bar_type: "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL",
        start: "2024-01-01", end: "2024-01-02", count: 1440 },
    ],
  }));
  render(<CatalogBrowser />);
  await waitFor(() => expect(screen.getByText("BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL")).toBeInTheDocument());
  expect(screen.getByText("1440")).toBeInTheDocument();
});

test("shows empty hint when no data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] }));
  render(<CatalogBrowser />);
  await waitFor(() => expect(screen.getByText("暂无数据")).toBeInTheDocument());
});
