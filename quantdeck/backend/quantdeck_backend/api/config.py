from fastapi import APIRouter, HTTPException

from quantdeck_backend.models.config import ExchangeCredentialIn
from quantdeck_backend.services import get_services

router = APIRouter()


@router.get("/api/lock-status")
def lock_status() -> dict:
    s = get_services()
    return {"unlocked": s.store.is_unlocked(), "initialized": s.store.initialized()}


@router.post("/api/unlock")
def unlock(body: dict) -> dict:
    s = get_services()
    try:
        s.store.unlock(body.get("passphrase", ""))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail={"code": "bad_passphrase", "message": str(exc)})
    return {"unlocked": True}


def _require_unlock():
    s = get_services()
    if not s.store.is_unlocked():
        raise HTTPException(status_code=423, detail={"code": "locked", "message": "未解锁"})
    return s


@router.get("/api/exchanges")
def list_exchanges() -> list:
    s = _require_unlock()
    return [c.model_dump() for c in s.config.list_exchanges()]


@router.put("/api/exchanges/{name}")
def put_exchange(name: str, cred: ExchangeCredentialIn) -> dict:
    s = _require_unlock()
    s.config.set_exchange(name, cred)
    return {"ok": True}


@router.delete("/api/exchanges/{name}")
def delete_exchange(name: str) -> dict:
    s = _require_unlock()
    s.config.delete_exchange(name)
    return {"ok": True}


@router.post("/api/exchanges/{name}/test")
async def test_exchange(name: str) -> dict:
    s = _require_unlock()
    status = await s.config.test_connection(name)
    return status.model_dump()
