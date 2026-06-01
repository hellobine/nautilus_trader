from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.objects import Price, Quantity

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

_INTERVAL_SPEC = {
    "1m": "1-MINUTE",
    "5m": "5-MINUTE",
    "15m": "15-MINUTE",
    "1h": "1-HOUR",
    "4h": "4-HOUR",
    "1d": "1-DAY",
}


def instrument_id_str(market: str, symbol: str) -> str:
    sym = symbol.upper()
    return f"{sym}-PERP.BINANCE" if market == "futures" else f"{sym}.BINANCE"


def bar_type_str(market: str, symbol: str, interval: str) -> str:
    return f"{instrument_id_str(market, symbol)}-{_INTERVAL_SPEC[interval]}-LAST-EXTERNAL"


def kline_to_bar(market: str, symbol: str, interval: str, row: list) -> Bar:
    bt = BarType.from_str(bar_type_str(market, symbol, interval))
    close_ms = int(row[6])
    ts = close_ms * 1_000_000
    return Bar(
        bt,
        Price.from_str(str(row[1])),
        Price.from_str(str(row[2])),
        Price.from_str(str(row[3])),
        Price.from_str(str(row[4])),
        Quantity.from_str(str(row[5])),
        ts,
        ts,
    )
