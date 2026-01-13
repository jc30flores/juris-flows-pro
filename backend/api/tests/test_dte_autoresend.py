import json
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from api.dte_cf_service import resend_pending_dtes
from api.models import Client, Invoice, InvoiceItem, Service, ServiceCategory


class DummyResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or json.dumps(payload)

    def json(self):
        return self._payload


class ResendPendingDteTests(TestCase):
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
            number="FAC-0002",
            date=timezone.now().date(),
            client=self.client,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status="PENDIENTE",
            estado_dte="PENDIENTE",
            observations="",
            total="100.00",
            numero_control="DTE-01-M001P001-000000000000001",
            codigo_generacion="2F92B17B-1D7D-4D3F-9C29-6B0F830B1E4C",
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            service=service,
            quantity=1,
            unit_price="100.00",
            subtotal="100.00",
        )

    @patch("api.dte_cf_service.requests.post")
    def test_resend_pending_dte_updates_status(self, mock_post):
        mock_post.return_value = DummyResponse(
            {
                "success": True,
                "respuesta_hacienda": {"estado": "RECIBIDO", "descripcionMsg": "RECIBIDO"},
            }
        )

        resent = resend_pending_dtes(limit=10)
        self.invoice.refresh_from_db()

        self.assertEqual(resent, 1)
        self.assertEqual(self.invoice.dte_status, "ACEPTADO")
        self.assertEqual(self.invoice.estado_dte, "ACEPTADO")
        self.assertIsNotNone(self.invoice.last_dte_sent_at)
        self.assertGreaterEqual(self.invoice.dte_send_attempts, 1)
