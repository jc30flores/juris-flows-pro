import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        try:
            from .connectivity import CONNECTIVITY_SENTINEL

            if getattr(CONNECTIVITY_SENTINEL, "_started", False):
                return

            print("[CONNECTIVITY] Inicializando centinela de conectividad...")
            CONNECTIVITY_SENTINEL.start()
            CONNECTIVITY_SENTINEL._started = True
            print("[CONNECTIVITY] Centinela de conectividad iniciado.")
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to start connectivity sentinel")
