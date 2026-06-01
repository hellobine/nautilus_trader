import asyncio
import datetime as dt
import itertools
from collections.abc import Callable

from nautilus_trader.model.data import Bar

from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.convert import INTERVAL_MS, bar_type_str, kline_to_bar
from quantdeck_backend.models.config import DownloadJob, DownloadRequest

_counter = itertools.count(1)


def _to_ms(iso: str) -> int:
    s = iso.replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        d = dt.datetime.fromisoformat(s + "T00:00:00+00:00")
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return int(d.timestamp() * 1000)


class DownloadService:
    """从 Binance 下载 K 线写入 catalog，带任务登记与进度回调。"""

    def __init__(
        self,
        client,
        catalog: CatalogService,
        on_progress: Callable[[DownloadJob], None],
    ) -> None:
        self._client = client
        self._catalog = catalog
        self._on_progress = on_progress
        self._jobs: dict[str, DownloadJob] = {}

    def create_job(self, req: DownloadRequest) -> DownloadJob:
        job_id = f"dl-{next(_counter)}"
        start_ms, end_ms = _to_ms(req.start), _to_ms(req.end)
        total = 0
        for itv in req.intervals:
            total += max(0, (end_ms - start_ms) // INTERVAL_MS[itv])
        job = DownloadJob(
            id=job_id, request=req, status="pending", done=0, total=total,
            message="", created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        )
        self._jobs[job_id] = job
        return job

    def list(self) -> list[DownloadJob]:
        return list(self._jobs.values())

    def get(self, job_id: str) -> DownloadJob:
        return self._jobs[job_id]

    def start(self, req: DownloadRequest) -> DownloadJob:
        job = self.create_job(req)
        asyncio.create_task(self.run_job(job.id))
        return job

    async def run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = "running"
        self._on_progress(job)
        try:
            for itv in job.request.intervals:
                await self._download_interval(job, itv)
            job.status = "done"
            job.message = "完成"
        except Exception as exc:  # noqa: BLE001
            job.status = "error"
            job.message = str(exc)
        self._on_progress(job)

    async def _download_interval(self, job: DownloadJob, interval: str) -> None:
        req = job.request
        cur = _to_ms(req.start)
        end_ms = _to_ms(req.end)
        step = INTERVAL_MS[interval]
        while cur < end_ms:
            rows = await self._client.fetch_klines(
                req.market, req.symbol, interval, cur, end_ms, limit=1000
            )
            if not rows:
                break
            bars: list[Bar] = [kline_to_bar(req.market, req.symbol, interval, r) for r in rows]
            self._catalog.write_bars(bars)
            job.done += len(bars)
            self._on_progress(job)
            last_open = int(rows[-1][0])
            cur = last_open + step
            if len(rows) < 1000:
                break
