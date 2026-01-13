from unittest.mock import patch, Mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.connectivity import ConnectivitySentinel
from api.dte_cf_service import send_cf_dte_for_invoice
from api.models import Client, Invoice, InvoiceItem, Service, ServiceCategory


class InvoiceCreateTests(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.category = ServiceCategory.objects.create(name="Servicios", description="")
        self.service = Service.objects.create(
            code="SVC-1",
            name="Consulta",
            category=self.category,
            base_price="10.00",
        )
        self.client_obj = Client.objects.create(
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

    @patch("api.serializers.send_cf_dte_for_invoice")
    def test_create_invoice_without_override_reason(self, mock_send):
        payload = {
            "date": timezone.now().date().isoformat(),
            "client": self.client_obj.id,
            "doc_type": Invoice.CF,
            "payment_method": Invoice.CASH,
            "total": "10.00",
            "services": [
                {
                    "service_id": self.service.id,
                    "name": self.service.name,
                    "price": "10.00",
                    "quantity": 1,
                    "subtotal": "10.00",
                }
            ],
        }

        response = self.client_api.post("/api/invoices/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        invoice = Invoice.objects.get(id=response.data["id"])
        item = invoice.items.first()
        self.assertIsNotNone(item)
        self.assertEqual(item.override_reason, "")
        mock_send.assert_called_once()

    @patch("api.dte_cf_service.requests.post")
    def test_offline_safe_generates_identifiers_on_530(self, mock_post):
        mock_response = Mock(status_code=530, text="down")
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        invoice = Invoice.objects.create(
            number="INV-530",
            date=timezone.now().date(),
            client=self.client_obj,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status=Invoice.PENDING,
            observations="",
            total="10.00",
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            service=self.service,
            quantity=1,
            unit_price="10.00",
            subtotal="10.00",
            original_unit_price="10.00",
        )

        send_cf_dte_for_invoice(invoice)
        invoice.refresh_from_db()

        self.assertEqual(invoice.dte_status, Invoice.PENDING)
        self.assertTrue(invoice.numero_control)
        self.assertTrue(invoice.codigo_generacion)
        self.assertEqual(invoice.last_dte_error_code, "530")


class ConnectivityAutoresendTests(SimpleTestCase):
    @patch("api.dte_cf_service.autoresend_pending_invoices")
    @patch("api.connectivity.requests.get")
    def test_sentinel_transition_to_200_triggers_autoresend(
        self, mock_get, mock_autoresend
    ):
        def build_response(status_code: int):
            response = Mock()
            response.status_code = status_code
            return response

        mock_get.side_effect = [
            build_response(200),
            build_response(530),
            build_response(200),
            build_response(200),
        ]

        sentinel = ConnectivitySentinel(
            internet_url="http://example.com/internet",
            api_url="http://example.com/api",
            interval=1,
            timeout=1,
        )
        sentinel.run_once()
        sentinel.run_once()

        mock_autoresend.assert_called_once()
