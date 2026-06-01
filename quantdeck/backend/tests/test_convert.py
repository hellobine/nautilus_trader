from nautilus_trader.model.data import Bar

from quantdeck_backend.bridge.convert import (
    INTERVAL_MS,
    bar_type_str,
    kline_to_bar,
)


def test_bar_type_str_spot_and_futures():
    assert bar_type_str("spot", "btcusdt", "1m") == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert bar_type_str("futures", "btcusdt", "1h") == "BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"


def test_interval_ms_table():
    assert INTERVAL_MS["1m"] == 60_000
    assert INTERVAL_MS["1d"] == 86_400_000


def test_kline_to_bar():
    row = [1700000000000, "100", "110", "90", "105", "12.5", 1700000059999, "0", 1, "0", "0", "0"]
    bar = kline_to_bar("spot", "BTCUSDT", "1m", row)
    assert isinstance(bar, Bar)
    assert str(bar.bar_type) == "BTCUSDT.BINANCE-1-MINUTE-LAST-EXTERNAL"
    assert str(bar.close) == "105"
    # ts_event 取 closeTime（ms→ns）
    assert bar.ts_event == 1700000059999 * 1_000_000
