from dataclasses import dataclass

from quantdeck_backend.api.ws import hub
from quantdeck_backend.bridge.binance_client import BinanceKlineClient
from quantdeck_backend.bridge.catalog_service import CatalogService
from quantdeck_backend.bridge.config_service import ConfigService
from quantdeck_backend.bridge.download_service import DownloadService
from quantdeck_backend.bridge.secrets import SecretStore
from quantdeck_backend.config import get_settings
from quantdeck_backend.models.config import DownloadJob


@dataclass
class Services:
    store: SecretStore
    config: ConfigService
    catalog: CatalogService
    downloads: DownloadService

    @classmethod
    def build(cls) -> "Services":
        settings = get_settings()
        store = SecretStore(settings.secrets_path)
        client = BinanceKlineClient()
        config = ConfigService(store, client)
        catalog = CatalogService(settings.catalog_dir)

        def on_progress(job: DownloadJob) -> None:
            hub.broadcast_threadsafe(
                {"type": "download_progress", "job": job.model_dump()}
            )

        downloads = DownloadService(client, catalog, on_progress=on_progress)
        return cls(store=store, config=config, catalog=catalog, downloads=downloads)


_SERVICES: "Services | None" = None


def get_services() -> "Services":
    global _SERVICES
    if _SERVICES is None:
        _SERVICES = Services.build()
    return _SERVICES
