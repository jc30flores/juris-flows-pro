import logging
import os

logger = logging.getLogger(__name__)

PROD_BASE_URL = "https://p12152606851014.cheros.dev"
VALID_MH_AMBIENTES = {"00", "01"}

_LOGGED = False


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def get_mh_ambiente() -> str:
    value = (
        os.getenv("MH_AMBIENTE")
        or os.getenv("DTE_AMBIENTE")
        or os.getenv("HACIENDA_AMBIENTE")
    )
    if value is None or not value.strip():
        value = "01"
    value = value.strip()
    if value not in VALID_MH_AMBIENTES:
        raise ValueError(
            f"Invalid MH_AMBIENTE '{value}'. Expected one of {sorted(VALID_MH_AMBIENTES)}."
        )
    return value


def get_dte_base_url() -> str:
    value = os.getenv("DTE_BASE_URL") or os.getenv("DTE_ENDPOINT") or os.getenv("DTE_API_URL")
    if value and value.strip():
        return _normalize_url(value)
    ambiente = get_mh_ambiente()
    if ambiente == "00":
        raise ValueError(
            "MH_AMBIENTE is set to '00' but DTE_BASE_URL is not configured. "
            "Set DTE_BASE_URL to the testing endpoint."
        )
    return PROD_BASE_URL


def build_dte_url(path: str) -> str:
    base_url = get_dte_base_url()
    return f"{base_url}/{path.lstrip('/')}"


def log_dte_configuration() -> None:
    global _LOGGED
    if _LOGGED:
        return
    base_url = get_dte_base_url()
    ambiente = get_mh_ambiente()
    logger.info("DTE config resolved: base_url=%s mh_ambiente=%s", base_url, ambiente)
    print(f"[DTE CONFIG] base_url={base_url} mh_ambiente={ambiente}")
    _LOGGED = True
