import json
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from api.dte_cf_service import send_dte_for_invoice
from api.models import Client, Invoice, InvoiceItem, Service, ServiceCategory


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)
        self.status_code = 200

    def json(self):
        return self._payload


class SendCFDteTests(TestCase):
    def setUp(self):
        category = ServiceCategory.objects.create(
            name="Consultoria",
            description="Servicios legales",
        )
        service = Service.objects.create(
            code="SRV-001",
            name="Consulta",
            category=category,
            base_price="100.00",
        )
        self.client = Client.objects.create(
            full_name="Juan Perez",
            company_name="",
            client_type=Client.CF,
            dui="",
            nit="06142412061012",
            nrc="",
            phone="71234567",
            email="juan@example.com",
            direccion="Colonia Centro",
        )
        self.invoice = Invoice.objects.create(
            number="FAC-0001",
            date=timezone.now().date(),
            client=self.client,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status=Invoice.PENDING,
            observations="",
            total="100.00",
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            service=service,
            quantity=1,
            unit_price="100.00",
            subtotal="100.00",
        )

    @patch("api.dte_cf_service.requests.post")
    def test_send_cf_includes_docu_recibe(self, mock_post):
        mock_post.return_value = DummyResponse(
            {
                "success": True,
                "respuesta_hacienda": {"estado": "RECIBIDO", "descripcionMsg": "RECIBIDO"},
            }
        )

        record = send_dte_for_invoice(self.invoice, ensure_identifiers=True)

        payload = record.request_payload
        self.assertEqual(
            payload["dte"]["extension"]["docuRecibe"],
            self.client.nit,
        )
