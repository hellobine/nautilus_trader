import pytest

from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.download_service import DownloadService
from quantdeck_backend.models.config import DownloadRequest


class FakeClient:
    def __init__(self, pages):
        self._pages = pages
        self.calls = 0

    async def fetch_klines(self, market, symbol, interval, start_ms, end_ms, limit=1000, testnet=False):
        page = self._pages[self.calls] if self.calls < len(self._pages) else []
        self.calls += 1
        return page


def _row(open_ms, close_ms, price):
    return [open_ms, str(price), str(price + 1), str(price - 1), str(price), "1.0", close_ms, "0", 1, "0", "0", "0"]


@pytest.mark.asyncio
async def test_run_job_writes_bars_and_reports_progress(tmp_path):
    # 两页，第二页空 → 结束
    page1 = [_row(i * 60_000, i * 60_000 + 59_999, 100 + i) for i in range(3)]
    client = FakeClient([page1, []])
    catalog = CatalogService(str(tmp_path))
    events = []
    svc = DownloadService(client, catalog, on_progress=events.append)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    await svc.run_job(job.id)

    done_job = svc.get(job.id)
    assert done_job.status == "done"
    assert done_job.done == 3
    # catalog 里应有 3 根 bar
    entries = catalog.list_entries()
    assert entries[0].count == 3
    # 进度回调至少触发一次
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_run_job_error_marks_status(tmp_path):
    class BoomClient:
        async def fetch_klines(self, *a, **k):
            raise RuntimeError("boom")

    catalog = CatalogService(str(tmp_path))
    svc = DownloadService(BoomClient(), catalog, on_progress=lambda j: None)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    await svc.run_job(job.id)
    assert svc.get(job.id).status == "error"


def test_list_and_get(tmp_path):
    catalog = CatalogService(str(tmp_path))
    svc = DownloadService(None, catalog, on_progress=lambda j: None)
    req = DownloadRequest(market="spot", symbol="BTCUSDT", intervals=["1m"], start="1970-01-01", end="1970-01-02")
    job = svc.create_job(req)
    assert svc.list()[0].id == job.id
    assert svc.get(job.id).id == job.id
