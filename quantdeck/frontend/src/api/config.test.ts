import { afterEach, expect, test, vi } from "vitest";
import { getLockStatus, unlock, listExchanges } from "./config";

afterEach(() => vi.restoreAllMocks());

function stubJson(data: unknown, ok = true) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 423, json: async () => data }));
}

test("getLockStatus parses response", async () => {
  stubJson({ unlocked: false, initialized: true });
  const s = await getLockStatus();
  expect(s.unlocked).toBe(false);
});

test("unlock posts passphrase", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ unlocked: true }) });
  vi.stubGlobal("fetch", fetchMock);
  await unlock("pw");
  expect(fetchMock).toHaveBeenCalledWith("/api/unlock", expect.objectContaining({ method: "POST" }));
});

test("listExchanges returns array", async () => {
  stubJson([{ name: "binance", api_key: "abcd****ghij", testnet: false }]);
  const list = await listExchanges();
  expect(list[0].name).toBe("binance");
});
