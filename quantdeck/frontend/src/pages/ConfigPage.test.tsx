import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ConfigPage } from "./index";

afterEach(() => vi.restoreAllMocks());

test("renders all four sections when unlocked", async () => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string) => {
    if (url === "/api/lock-status") {
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ unlocked: true, initialized: true }) });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => [] });
  }));
  render(<ConfigPage wsFactory={() => ({ close: () => {} })} />);
  await waitFor(() => expect(screen.getByText("交易所凭证（Binance）")).toBeInTheDocument());
  expect(screen.getByText("数据目录")).toBeInTheDocument();
  expect(screen.getByText("下载历史数据")).toBeInTheDocument();
});
