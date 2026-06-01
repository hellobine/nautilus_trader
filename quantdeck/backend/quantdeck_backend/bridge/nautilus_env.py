from dataclasses import dataclass


@dataclass
class NautilusInfo:
    available: bool
    version: str | None
    error: str | None


def probe_nautilus() -> NautilusInfo:
    """探测 nautilus_trader 是否可导入，返回版本或错误信息。"""
    try:
        import nautilus_trader

        return NautilusInfo(
            available=True,
            version=getattr(nautilus_trader, "__version__", "unknown"),
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — 探针需吞掉所有导入错误
        return NautilusInfo(available=False, version=None, error=str(exc))
