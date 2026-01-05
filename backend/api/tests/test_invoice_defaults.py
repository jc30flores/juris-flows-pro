from django.test import TestCase
from django.utils import timezone

from api.models import Client, Invoice


class InvoiceDefaultsTests(TestCase):
    def test_invoice_has_credit_note_defaults_false(self):
        client = Client.objects.create(
            full_name="Cliente Prueba",
            company_name="",
            client_type=Client.CF,
            dui="",
            nit="",
            nrc="",
            phone="",
            email="",
            direccion="",
        )
        invoice = Invoice.objects.create(
            number="INV-DEFAULT-1",
            date=timezone.now().date(),
            client=client,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status=Invoice.PENDING,
            observations="",
            total="10.00",
        )

        self.assertFalse(invoice.has_credit_note)
