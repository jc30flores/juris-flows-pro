import json
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import Client, DTERecord, Invoice, InvoiceItem, Service, ServiceCategory


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class InvoiceResendDteTests(TestCase):
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
        self.client_record = Client.objects.create(
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
            client=self.client_record,
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
        DTERecord.objects.create(
            invoice=self.invoice,
            dte_type="CF",
            status="PENDIENTE",
            control_number="DTE-01-M002P001-000000000000001",
            issuer_nit="12101304761012",
            receiver_nit=self.client_record.nit,
            receiver_name=self.client_record.full_name,
            issue_date=self.invoice.date,
            total_amount=self.invoice.total,
            request_payload={
                "dte": {
                    "identificacion": {
                        "codigoGeneracion": "ABC-123",
                        "numeroControl": "DTE-01-M002P001-000000000000001",
                        "fecEmi": "2024-01-01",
                        "horEmi": "00:00:00",
                    }
                }
            },
        )

    @patch("api.dte_cf_service.requests.post")
    def test_resend_dte_returns_success(self, mock_post):
        mock_post.return_value = DummyResponse(
            {
                "success": True,
                "uuid": "UUID-123",
                "respuesta_hacienda": {
                    "estado": "RECIBIDO",
                    "descripcionMsg": "RECIBIDO",
                },
            }
        )

        client = APIClient()
        response = client.post(f"/api/invoices/{self.invoice.id}/resend-dte/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["invoice_id"], self.invoice.id)
        self.assertEqual(payload["dte_status"], "ACEPTADO")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.dte_send_attempts, 1)
        self.assertIsNotNone(self.invoice.last_dte_sent_at)

    def test_resend_dte_missing_invoice(self):
        client = APIClient()
        response = client.post("/api/invoices/999999/resend-dte/")
        self.assertEqual(response.status_code, 404)
