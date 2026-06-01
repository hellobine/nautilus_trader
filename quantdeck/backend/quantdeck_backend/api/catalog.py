from fastapi import APIRouter

from quantdeck_backend.services import get_services

router = APIRouter()


@router.get("/api/catalog")
def list_catalog() -> list:
    s = get_services()
    return [e.model_dump() for e in s.catalog.list_entries()]
