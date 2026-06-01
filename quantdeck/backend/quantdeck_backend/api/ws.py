from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class WsHub:
    """管理活动 WebSocket 连接，支持广播。"""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, message: dict) -> None:
        for ws in list(self._clients):
            await ws.send_json(message)

    def broadcast_threadsafe(self, message: dict) -> None:
        """供同步回调触发广播：在当前事件循环里调度 broadcast。"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # 无运行中的事件循环（如纯同步测试），静默跳过
        loop.create_task(self.broadcast(message))


hub = WsHub()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await hub.connect(ws)
    await ws.send_json({"type": "welcome"})
    try:
        while True:
            data = await ws.receive_json()
            await ws.send_json({"type": "echo", "payload": data})
    except WebSocketDisconnect:
        hub.disconnect(ws)
