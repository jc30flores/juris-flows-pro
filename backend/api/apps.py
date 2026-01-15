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
        if not getattr(settings, "CONNECTIVITY_SENTINEL_ENABLED", True):
            return
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return
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
