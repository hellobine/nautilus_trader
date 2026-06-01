from fastapi import APIRouter

from quantdeck_backend.bridge.nautilus_env import probe_nautilus

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    info = probe_nautilus()
    return {
        "status": "ok",
        "nautilus": {
            "available": info.available,
            "version": info.version,
            "error": info.error,
        },
    }
