from fastapi import APIRouter, HTTPException

from quantdeck_backend.models.config import DownloadRequest
from quantdeck_backend.services import get_services

router = APIRouter()


@router.post("/api/downloads")
async def create_download(req: DownloadRequest) -> dict:
    # async 路由：确保 start() 内的 asyncio.create_task 有运行中的事件循环
    s = get_services()
    job = s.downloads.start(req)
    return job.model_dump()


@router.get("/api/downloads")
def list_downloads() -> list:
    s = get_services()
    return [j.model_dump() for j in s.downloads.list()]


@router.get("/api/downloads/{job_id}")
def get_download(job_id: str) -> dict:
    s = get_services()
    try:
        return s.downloads.get(job_id).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "任务不存在"})
