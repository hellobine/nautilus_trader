export type WsHandler = (message: unknown) => void;

export interface WsClient {
  close: () => void;
}

export function createWsClient(
  path: string,
  onMessage: WsHandler,
  reconnectMs = 2000,
): WsClient {
  let socket: WebSocket | null = null;
  let closedByUser = false;

  const url =
    path.startsWith("ws://") || path.startsWith("wss://")
      ? path
      : `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${path}`;

  const connect = () => {
    socket = new WebSocket(url);
    socket.onmessage = (e) => {
      try {
        onMessage(JSON.parse(e.data));
      } catch {
        /* 忽略非 JSON 帧 */
      }
    };
    socket.onclose = () => {
      if (!closedByUser) setTimeout(connect, reconnectMs);
    };
  };

  connect();

  return {
    close: () => {
      closedByUser = true;
      socket?.close();
    },
  };
}
