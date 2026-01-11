from typing import Optional

from django.conf import settings
from django.core import signing

from .models import StaffUser


def get_staff_user_from_request(request) -> Optional[StaffUser]:
    user_id = (
        request.headers.get("X-Staff-User")
        or request.query_params.get("user_id")
        or request.data.get("user_id")
    )
    if not user_id:
        return None
    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        return None
    return StaffUser.objects.filter(id=user_id_int, is_active=True).first()


def generate_price_override_token(staff_user: Optional[StaffUser]) -> str:
    signer = signing.TimestampSigner()
    staff_user_id = staff_user.id if staff_user else "anonymous"
    return signer.sign(str(staff_user_id))


def validate_price_override_token(token: str, staff_user: Optional[StaffUser]) -> bool:
    if not token:
        return False
    signer = signing.TimestampSigner()
    max_age = getattr(settings, "PRICE_OVERRIDE_TOKEN_MAX_AGE_SECONDS", 300)
    try:
        value = signer.unsign(token, max_age=max_age)
    except signing.BadSignature:
        return False
    expected = str(staff_user.id) if staff_user else "anonymous"
    return value == expected
