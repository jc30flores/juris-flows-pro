from django.conf import settings

DEFAULT_DTE_TOKEN = "api_key_cliente_12152606851014"


def build_dte_headers() -> dict:
    token = getattr(settings, "DTE_API_TOKEN", "").strip() or DEFAULT_DTE_TOKEN
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def mask_headers(headers: dict) -> dict:
    masked = dict(headers)
    auth = masked.get("Authorization")
    if auth:
        masked["Authorization"] = "Bearer ***"
    return masked
