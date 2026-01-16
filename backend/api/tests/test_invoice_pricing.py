from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from api.models import Client, Invoice, Service, ServiceCategory
from api.serializers import InvoiceSerializer


class InvoicePricingTests(TestCase):
    def setUp(self):
        self.category = ServiceCategory.objects.create(
            name="Servicios",
            description="Categoría base",
        )
        self.client = Client.objects.create(
            full_name="Cliente Demo",
            company_name="",
            client_type=Client.CF,
            dui="",
            nit="06142412061012",
            nrc="",
            phone="71234567",
            email="cliente@example.com",
            direccion="Zona Centro",
        )

    @patch("api.serializers.send_dte_for_invoice")
    def test_invoice_accepts_unit_and_wholesale_prices(self, mock_send):
        mock_send.return_value = None
        service_unit = Service.objects.create(
            code="SRV-UNIT",
            name="Servicio Unitario",
            category=self.category,
            unit_price="10.00",
            wholesale_price="8.00",
        )
        service_fallback = Service.objects.create(
            code="SRV-FALL",
            name="Servicio sin mayoreo",
            category=self.category,
            unit_price="12.00",
            wholesale_price=None,
        )

        serializer = InvoiceSerializer(
            data={
                "date": timezone.now().date(),
                "client": self.client.id,
                "doc_type": Invoice.CF,
                "payment_method": Invoice.CASH,
                "services": [
                    {
                        "service_id": service_unit.id,
                        "quantity": 2,
                        "price_type": "WHOLESALE",
                    },
                    {
                        "service_id": service_fallback.id,
                        "quantity": 1,
                        "price_type": "WHOLESALE",
                    },
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        invoice = serializer.save()
        items = list(invoice.items.order_by("service_id"))

        first = items[0]
        self.assertEqual(first.price_type, "WHOLESALE")
        self.assertEqual(str(first.unit_price_snapshot), "10.00")
        self.assertEqual(str(first.wholesale_price_snapshot), "8.00")
        self.assertEqual(str(first.applied_unit_price), "8.00")
        self.assertEqual(str(first.unit_price), "8.00")
        self.assertEqual(str(first.line_subtotal), "16.00")

        second = items[1]
        self.assertEqual(second.price_type, "WHOLESALE")
        self.assertEqual(str(second.unit_price_snapshot), "12.00")
        self.assertIsNone(second.wholesale_price_snapshot)
        self.assertEqual(str(second.applied_unit_price), "12.00")
        self.assertEqual(str(second.unit_price), "12.00")
        self.assertEqual(str(second.line_subtotal), "12.00")
