import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { useHealth } from "./useHealth";

afterEach(() => vi.restoreAllMocks());

test("useHealth fetches and exposes status", async () => {
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

  const { result } = renderHook(() => useHealth());
  await waitFor(() => expect(result.current.health?.status).toBe("ok"));
  expect(result.current.health?.nautilus.version).toBe("1.0.0");
});
