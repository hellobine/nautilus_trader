import { afterEach, expect, test, vi } from "vitest";
import { createWsClient } from "./ws";

class FakeWS {
  static instances: FakeWS[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  readyState = 0;
  constructor(public url: string) {
    FakeWS.instances.push(this);
  }
  send() {}
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

afterEach(() => {
  FakeWS.instances = [];
  vi.restoreAllMocks();
});

test("delivers parsed messages to handler", () => {
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  const received: unknown[] = [];
  createWsClient("/ws", (msg) => received.push(msg));
  const ws = FakeWS.instances[0];
  ws.onopen?.();
  ws.onmessage?.({ data: JSON.stringify({ type: "welcome" }) });
  expect(received).toEqual([{ type: "welcome" }]);
});

test("reconnects after close", () => {
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  createWsClient("/ws", () => {});
  expect(FakeWS.instances.length).toBe(1);
  FakeWS.instances[0].close();
  vi.advanceTimersByTime(2000);
  expect(FakeWS.instances.length).toBe(2);
  vi.useRealTimers();
});
