from quantdeck_backend.bridge.nautilus_env import probe_nautilus


def test_probe_reports_available_and_version():
    info = probe_nautilus()
    assert info.available is True
    assert info.version  # 非空字符串
    assert info.error is None
