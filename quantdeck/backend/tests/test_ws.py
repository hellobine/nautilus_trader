from fastapi.testclient import TestClient

from quantdeck_backend.main import create_app


def test_ws_echo_and_welcome():
    client = TestClient(create_app())
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "welcome"
        ws.send_json({"type": "ping"})
        echo = ws.receive_json()
        assert echo == {"type": "echo", "payload": {"type": "ping"}}
