import logging
import random
import threading
import time
from typing import Dict, Tuple

import requests
from django.conf import settings
from django.utils import timezone

from .dte_urls import get_dte_base_url
logger = logging.getLogger(__name__)


def _resolve_connectivity_url() -> str | None:
    override_url = str(getattr(settings, "CONNECTIVITY_CHECK_URL", "") or "").strip()
    if override_url:
        return override_url
    dte_base_url = get_dte_base_url()
    if dte_base_url:
        return f"{dte_base_url.rstrip('/')}/health"
    return None


DEFAULT_INTERNET_URL = _resolve_connectivity_url()
DEFAULT_API_URL = getattr(
    settings, "API_HEALTH_URL", "http://localhost:8000/api/health/"
)
DEFAULT_INTERVAL = getattr(settings, "CONNECTIVITY_CHECK_INTERVAL", 15)
DEFAULT_TIMEOUT = getattr(settings, "CONNECTIVITY_CHECK_TIMEOUT", 5)

CONNECTIVITY_STATUS: Dict[str, Dict[str, object]] = {
    "internet": {
        "ok": False,
        "last_ok": None,
        "last_error": None,
        "reason": "init",
    },
    "api": {
        "ok": False,
        "last_ok": None,
        "last_error": None,
        "reason": "init",
    },
}


class ConnectivitySentinel:
    def __init__(
        self,
        internet_url: str = DEFAULT_INTERNET_URL,
        api_url: str = DEFAULT_API_URL,
        interval: int = DEFAULT_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.internet_url = internet_url
        self.api_url = api_url
        self.interval = interval
        self.timeout = timeout
        self._started = False
        self._thread: threading.Thread | None = None
        self._last_api_ok: bool | None = None

    @property
    def started(self) -> bool:
        return self._started

    def _mark_status(self, key: str, ok: bool, reason: str) -> None:
        now_iso = timezone.now().isoformat()
        entry = CONNECTIVITY_STATUS[key]
        previous_ok = entry.get("ok")
        previous_reason = entry.get("reason")
        entry["ok"] = ok
        entry["reason"] = reason
        if ok:
            entry["last_ok"] = now_iso
        else:
            entry["last_error"] = now_iso
        if previous_ok != ok or previous_reason != reason:
            logger.info(
                "Connectivity status changed target=%s ok=%s reason=%s",
                key,
                ok,
                reason,
            )

    def _check_target(self, target: str, url: str) -> Tuple[bool, str]:
        if not url:
            return False, "not_configured"
        target_name = target.lower()
        try:
            response = requests.get(url, timeout=self.timeout)
            status_code = response.status_code
            if status_code in (200, 204):
                return True, "ok"
            reason = f"status_{status_code}"
            logger.warning(
                "Connectivity check failed target=%s status=%s reason=%s",
                target_name,
                status_code,
                reason,
            )
            return False, reason
        except requests.RequestException as exc:  # pragma: no cover - external IO
            logger.warning("Connectivity check failed for %s: %s", target, exc)
            return False, f"network_error:{exc}"

    def run_once(self) -> None:
        internet_ok, internet_reason = self._check_target("internet", self.internet_url)
        self._mark_status("internet", internet_ok, internet_reason if not internet_ok else "none")
        api_ok, api_reason = self._check_target("api", self.api_url)
        self._mark_status("api", api_ok, api_reason if not api_ok else "none")
        if api_ok and self._last_api_ok is not True:
            self._handle_api_recovered()
        self._last_api_ok = api_ok

    def _handle_api_recovered(self) -> None:
        try:
            from .dte_autoresend import autoresend_pending_invoices

            total = autoresend_pending_invoices()
            print(f"[CONNECTIVITY] API disponible. Autoresend DTE pendientes: {total}.")
        except Exception:  # pragma: no cover - defensive
            logger.exception("Failed to autoresend pending DTE after API recovery")

    def _loop(self) -> None:
        self.run_once()
        while True:
            try:
                self.run_once()
            except Exception:  # pragma: no cover - defensive
                logger.exception("Connectivity sentinel run_once failed")
            sleep_for = self.interval + random.uniform(0, max(1.0, self.interval * 0.1))
            time.sleep(sleep_for)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()


CONNECTIVITY_SENTINEL = ConnectivitySentinel()


def get_connectivity_status() -> Dict[str, Dict[str, object]]:
    return {key: value.copy() for key, value in CONNECTIVITY_STATUS.items()}
