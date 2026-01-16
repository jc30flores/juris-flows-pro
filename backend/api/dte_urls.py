from .dte_config import get_dte_base_url


def build_dte_url(path: str) -> str:
    base_url = get_dte_base_url()
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}{path}"
