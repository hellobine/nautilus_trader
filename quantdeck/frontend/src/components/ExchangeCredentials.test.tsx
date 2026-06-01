import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ExchangeCredentials } from "./ExchangeCredentials";

afterEach(() => vi.restoreAllMocks());

test("lists existing credentials", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true, status: 200,
    json: async () => [{ name: "binance", api_key: "abcd****ghij", testnet: false }],
  }));
  render(<ExchangeCredentials />);
  await waitFor(() => expect(screen.getByText("abcd****ghij")).toBeInTheDocument());
});

test("submits new credential", async () => {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal("fetch", vi.fn().mockImplementation((url: string, opts?: { method?: string }) => {
    calls.push({ url, method: opts?.method ?? "GET" });
    return Promise.resolve({ ok: true, status: 200, json: async () => (url === "/api/exchanges" ? [] : { ok: true }) });
  }));
  render(<ExchangeCredentials />);
  await waitFor(() => expect(screen.getByLabelText("API Key")).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("API Key"), { target: { value: "mykey" } });
  fireEvent.change(screen.getByLabelText("API Secret"), { target: { value: "mysecret" } });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  await waitFor(() => expect(calls.some((c) => c.method === "PUT" && c.url === "/api/exchanges/binance")).toBe(true));
});
