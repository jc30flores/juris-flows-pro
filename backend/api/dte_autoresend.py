import logging
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from .dte_cf_service import send_dte_for_invoice
from .models import Invoice

logger = logging.getLogger(__name__)


def _pending_queryset(*, backoff_seconds: int):
    queryset = Invoice.objects.filter(dte_status__iexact=Invoice.PENDING, dte_is_sending=False)
    if backoff_seconds > 0:
        threshold = timezone.now() - timedelta(seconds=backoff_seconds)
        queryset = queryset.filter(
            models.Q(last_dte_sent_at__isnull=True) | models.Q(last_dte_sent_at__lte=threshold)
        )
    return queryset


def _reserve_pending_invoices(*, limit: int, backoff_seconds: int):
    with transaction.atomic():
        invoices = list(
            _pending_queryset(backoff_seconds=backoff_seconds)
            .select_for_update(skip_locked=True)
            .order_by("id")[:limit]
        )
        for invoice in invoices:
            invoice.dte_is_sending = True
            invoice.save(update_fields=["dte_is_sending"])
    return invoices


def autoresend_pending_invoices(*, limit: int | None = None) -> int:
    backoff_seconds = int(getattr(settings, "DTE_AUTORETRY_BACKOFF_SECONDS", 60))
    batch_limit = int(getattr(settings, "DTE_AUTORETRY_BATCH_SIZE", 25))
    limit = limit or batch_limit

    invoices = _reserve_pending_invoices(limit=limit, backoff_seconds=backoff_seconds)
    if not invoices:
        return 0

    sent = 0
    for invoice in invoices:
        try:
            send_dte_for_invoice(
                invoice,
                force_now_timestamp=True,
                ensure_identifiers=True,
            )
            sent += 1
        except Exception:  # pragma: no cover - defensive
            logger.exception("Autoresend failed for invoice %s", invoice.id)
        finally:
            invoice.dte_is_sending = False
            invoice.save(update_fields=["dte_is_sending"])
    return sent
