import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    _connectivity_started = False

    def ready(self):
        if self._connectivity_started:
            return
        try:
            from .connectivity import CONNECTIVITY_SENTINEL

            CONNECTIVITY_SENTINEL.start()
            self._connectivity_started = True
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to start connectivity sentinel")
