from quantdeck_backend.services import Services


def test_services_singletons(tmp_path, monkeypatch):
    monkeypatch.setenv("QD_CATALOG_DIR", str(tmp_path / "cat"))
    monkeypatch.setenv("QD_SECRETS_PATH", str(tmp_path / "secrets.enc"))
    svcs = Services.build()
    assert svcs.config is not None
    assert svcs.catalog is not None
    assert svcs.downloads is not None
    # downloads 与 config 共用同一个 SecretStore 实例
    assert svcs.config.store is svcs.store
