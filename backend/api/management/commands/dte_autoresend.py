import time

from django.core.management.base import BaseCommand

from api.dte_cf_service import check_hacienda_online, resend_pending_dtes


class Command(BaseCommand):
    help = "Reenvía DTE pendientes cuando Hacienda/API está disponible."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Ejecuta una sola vez.")
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help="Intervalo en segundos entre verificaciones cuando la API está online.",
        )
        parser.add_argument(
            "--initial-backoff",
            type=int,
            default=10,
            help="Backoff inicial en segundos cuando la API está offline.",
        )
        parser.add_argument(
            "--max-backoff",
            type=int,
            default=60,
            help="Backoff máximo en segundos cuando la API está offline.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Máximo de facturas pendientes a reenviar por ciclo.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        interval = max(1, int(options["interval"]))
        backoff = max(1, int(options["initial_backoff"]))
        max_backoff = max(backoff, int(options["max_backoff"]))
        limit = max(1, int(options["limit"]))

        while True:
            is_online = check_hacienda_online()
            if is_online:
                resent = resend_pending_dtes(limit=limit)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Hacienda online. Reenvíos ejecutados: {resent}."
                    )
                )
                backoff = max(1, int(options["initial_backoff"]))
                sleep_for = interval
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Hacienda offline. Reintentando en {backoff}s."
                    )
                )
                sleep_for = backoff
                backoff = min(max_backoff, backoff * 3)

            if once:
                break
            time.sleep(sleep_for)
