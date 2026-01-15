from django.core.management.base import BaseCommand

from api.dte_autoresend import autoresend_pending_invoices


class Command(BaseCommand):
    help = "Reenvía automáticamente los DTE pendientes."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Límite de facturas a reenviar.")

    def handle(self, *args, **options):
        limit = options.get("limit")
        sent = autoresend_pending_invoices(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"DTE autoresend completado. Total enviados: {sent}."))
