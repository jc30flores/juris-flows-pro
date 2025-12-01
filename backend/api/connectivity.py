import logging
import random
import threading
import time
from typing import Dict

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_INTERNET_URL = getattr(
    settings, "INTERNET_HEALTH_URL", "https://www.google.com/generate_204"
)
DEFAULT_API_URL = getattr(
    settings, "API_HEALTH_URL", "https://t12101304761012.cheros.dev/health"
)
DEFAULT_INTERVAL = getattr(settings, "CONNECTIVITY_CHECK_INTERVAL", 15)
DEFAULT_TIMEOUT = getattr(settings, "CONNECTIVITY_CHECK_TIMEOUT", 5)

CONNECTIVITY_STATUS: Dict[str, Dict[str, object]] = {
    "internet": {
        "ok": False,
        "last_ok": None,
        "last_fail": None,
        "reason": "init",
    },
    "api": {
        "ok": False,
        "last_ok": None,
        "last_fail": None,
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

    @property
    def started(self) -> bool:
        return self._started

    def _mark_status(self, key: str, ok: bool, reason: str) -> None:
        now_iso = timezone.now().isoformat()
        entry = CONNECTIVITY_STATUS[key]
        entry["ok"] = ok
        entry["reason"] = reason
        if ok:
            entry["last_ok"] = now_iso
        else:
            entry["last_fail"] = now_iso

    def run_once(self) -> None:
        internet_ok = False
        internet_reason = "none"
        try:
            response = requests.get(self.internet_url, timeout=self.timeout)
            if response.status_code in (200, 204):
                internet_ok = True
            else:
                internet_reason = f"status_{response.status_code}"
        except requests.RequestException as exc:
            internet_reason = f"network_error: {exc}"

        self._mark_status("internet", internet_ok, internet_reason if not internet_ok else "none")

        if not internet_ok:
            self._mark_status("api", False, "internet_down")
            return

        api_ok = False
        api_reason = "none"
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
            if response.status_code == 200:
                api_ok = True
            else:
                api_reason = f"status_{response.status_code}"
        except requests.RequestException as exc:
            api_reason = f"network_error: {exc}"

        self._mark_status("api", api_ok, api_reason if not api_ok else "none")

    def _loop(self) -> None:
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
        self.run_once()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()


CONNECTIVITY_SENTINEL = ConnectivitySentinel()


def get_connectivity_status() -> Dict[str, Dict[str, object]]:
    return {key: value.copy() for key, value in CONNECTIVITY_STATUS.items()}
