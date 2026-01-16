import logging
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)

DTE_BASE_PATH = "/api/v1/dte"
_DTE_BASE_URL_CACHE: str | None = None
_MH_AMBIENTE_CACHE: str | None = None


def _strip_dte_path(value: str) -> tuple[str, bool]:
    if DTE_BASE_PATH in value:
        base = value.split(DTE_BASE_PATH, 1)[0].rstrip("/")
        return base, True
    return value.rstrip("/"), False


def _normalize_base_url(raw_value: str, *, source_label: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    value, trimmed = _strip_dte_path(value)
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        if trimmed or parsed.path not in ("", "/"):
            logger.warning(
                "DTE base url normalized from %s; trimmed path=%s original=%s",
                source_label,
                trimmed or parsed.path,
                raw_value,
            )
        return f"{parsed.scheme}://{parsed.netloc}"
    if trimmed:
        logger.warning(
            "DTE base url normalized from %s; trimmed path=%s original=%s",
            source_label,
            DTE_BASE_PATH,
            raw_value,
        )
    return value


def get_dte_base_url() -> str:
    global _DTE_BASE_URL_CACHE  # noqa: PLW0603
    if _DTE_BASE_URL_CACHE is not None:
        return _DTE_BASE_URL_CACHE

    base_value = getattr(settings, "DTE_BASE_URL", "") or ""
    if base_value:
        base_url = _normalize_base_url(base_value, source_label="DTE_BASE_URL")
    else:
        fallback_value = getattr(settings, "DTE_API_BASE_URL", "") or ""
        if fallback_value:
            base_url = _normalize_base_url(
                fallback_value, source_label="DTE_API_BASE_URL"
            )
        else:
            legacy_value = (
                getattr(settings, "DTE_FACTURA_URL", "")
                or getattr(settings, "DTE_ENDPOINT_FACTURA", "")
                or ""
            )
            base_url = _normalize_base_url(
                legacy_value, source_label="DTE_FACTURA_URL"
            )

    _DTE_BASE_URL_CACHE = base_url or ""
    if _DTE_BASE_URL_CACHE:
        logger.info("DTE base url resolved to: %s", _DTE_BASE_URL_CACHE)
    return _DTE_BASE_URL_CACHE


def get_mh_ambiente() -> str:
    global _MH_AMBIENTE_CACHE  # noqa: PLW0603
    if _MH_AMBIENTE_CACHE is not None:
        return _MH_AMBIENTE_CACHE

    raw_value = (
        getattr(settings, "MH_AMBIENTE", "")
        or getattr(settings, "DTE_AMBIENTE", "")
        or ""
    )
    ambiente = str(raw_value).strip()
    if not ambiente:
        ambiente = "01"
    if ambiente not in {"00", "01"}:
        raise ValueError(
            f"MH_AMBIENTE inválido: '{ambiente}'. Valores permitidos: '00' o '01'."
        )
    _MH_AMBIENTE_CACHE = ambiente
    logger.info("MH ambiente resolved to: %s", _MH_AMBIENTE_CACHE)
    return _MH_AMBIENTE_CACHE
