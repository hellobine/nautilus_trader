import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { App } from "./App";

test("renders nav with five module links and health badge area", () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        nautilus: { available: true, version: "1.0.0", error: null },
      }),
    }),
  );
  render(<App />);
  expect(screen.getByRole("link", { name: "连接配置" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "回测分析" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "数据研究" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "实盘监控" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "策略控制" })).toBeInTheDocument();
});
