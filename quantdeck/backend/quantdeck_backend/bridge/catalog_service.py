import os

from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from quantdeck_backend.models.config import CatalogEntry


class CatalogService:
    """包 ParquetDataCatalog，列出已有 bar 数据。"""

    def __init__(self, catalog_dir: str) -> None:
        self._dir = catalog_dir
        os.makedirs(catalog_dir, exist_ok=True)
        self._cat = ParquetDataCatalog(catalog_dir)

    def write_bars(self, bars: list) -> None:
        """写入 bars（供下载服务调用，避免外部直接触碰 catalog 内部）。"""
        self._cat.write_data(bars)

    def _bar_type_dirs(self) -> list[str]:
        bar_root = os.path.join(self._dir, "data", "bar")
        if not os.path.isdir(bar_root):
            return []
        return sorted(
            name for name in os.listdir(bar_root)
            if os.path.isdir(os.path.join(bar_root, name))
        )

    def list_entries(self) -> list[CatalogEntry]:
        entries: list[CatalogEntry] = []
        for bt in self._bar_type_dirs():
            bars = self._cat.bars(bar_types=[bt])
            first = self._cat.query_first_timestamp(Bar, identifier=bt)
            last = self._cat.query_last_timestamp(Bar, identifier=bt)
            entries.append(
                CatalogEntry(
                    instrument_id=str(BarType.from_str(bt).instrument_id),
                    bar_type=bt,
                    start=str(first) if first is not None else None,
                    end=str(last) if last is not None else None,
                    count=len(bars),
                )
            )
        return entries
