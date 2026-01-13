import time

from django.core.management.base import BaseCommand
from django.db import transaction

from api.dte_cf_service import check_hacienda_online, transmit_invoice_dte
from api.models import Invoice


class Command(BaseCommand):
    help = "Reenvía automáticamente DTE pendientes cuando Hacienda vuelve a estar en línea."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Intervalo (segundos) entre ejecuciones cuando Hacienda está en línea.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25,
            help="Cantidad máxima de facturas pendientes por ciclo.",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        batch_size = options["batch_size"]
        backoff_steps = [10, 30, 60]
        backoff_index = 0

        self.stdout.write(self.style.NOTICE("Iniciando dte_autoresend..."))
        while True:
            if check_hacienda_online():
                backoff_index = 0
                self._resend_pending(batch_size)
                time.sleep(interval)
                continue

            sleep_for = backoff_steps[backoff_index]
            backoff_index = min(backoff_index + 1, len(backoff_steps) - 1)
            time.sleep(sleep_for)

    def _resend_pending(self, batch_size: int) -> None:
        while True:
            with transaction.atomic():
                pending_invoices = list(
                    Invoice.objects.select_for_update(skip_locked=True)
                    .filter(
                        dte_status=Invoice.PENDING,
                        numero_control__isnull=False,
                        codigo_generacion__isnull=False,
                    )
                    .order_by("id")[:batch_size]
                )

                if not pending_invoices:
                    return

                for invoice in pending_invoices:
                    transmit_invoice_dte(
                        invoice,
                        force_now_timestamp=True,
                        allow_generate_identifiers=True,
                        source="auto_resend",
                    )

            if len(pending_invoices) < batch_size:
                return
