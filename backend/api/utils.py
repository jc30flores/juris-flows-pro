from typing import Optional

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
