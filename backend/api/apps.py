import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        try:
            if not self._should_start_sentinel():
                return

            from .connectivity import CONNECTIVITY_SENTINEL

            if getattr(CONNECTIVITY_SENTINEL, "_started", False):
                return

            print("[CONNECTIVITY] Inicializando centinela de conectividad...")
            CONNECTIVITY_SENTINEL.start()
            CONNECTIVITY_SENTINEL._started = True
            print("[CONNECTIVITY] Centinela de conectividad iniciado.")
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to start connectivity sentinel")

    def _should_start_sentinel(self) -> bool:
        if not getattr(settings, "ENABLE_CONNECTIVITY_SENTINEL", True):
            return False

        argv = sys.argv
        if any("runserver" in arg for arg in argv):
            return os.environ.get("RUN_MAIN") == "true"

        server_markers = ("gunicorn", "uvicorn", "daphne", "uwsgi")
        return any(marker in arg for marker in server_markers for arg in argv)
