from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog

from quantdeck_backend.bridge.catalog_service import CatalogService


def _write_sample(path):
    cat = ParquetDataCatalog(path)
    bt = BarType.from_str("BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL")
    bars = [
        Bar(bt, Price.from_str("100"), Price.from_str("101"), Price.from_str("99"),
            Price.from_str("100"), Quantity.from_str("1"), i * 60_000_000_000, i * 60_000_000_000)
        for i in range(3)
    ]
    cat.write_data(bars)


def test_empty_catalog_returns_empty(tmp_path):
    svc = CatalogService(str(tmp_path))
    assert svc.list_entries() == []


def test_lists_written_bars(tmp_path):
    _write_sample(str(tmp_path))
    svc = CatalogService(str(tmp_path))
    entries = svc.list_entries()
    assert len(entries) == 1
    e = entries[0]
    assert e.bar_type == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert e.instrument_id == "BTCUSDT.BINANCE"
    assert e.count == 3
