from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.dte_invalidation_service import invalidate_dte_for_invoice
from api.models import Client, DTERecord, Invoice, InvoiceItem, Service, ServiceCategory


class DummyResponse:
    def __init__(self, payload, status_code=200, text=None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or ""

    def json(self):
        return self._payload


class DTEInvalidationTests(TestCase):
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
        self.client_obj = Client.objects.create(
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
            number="FAC-1001",
            date=timezone.now().date(),
            client=self.client_obj,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status=Invoice.APPROVED,
            observations="",
            total="100.00",
            numero_control="DTE-01-M001P001-000000000000101",
            codigo_generacion="4F92B17B-1D7D-4D3F-9C29-6B0F830B1E4C",
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            service=service,
            quantity=1,
            unit_price="100.00",
            subtotal="100.00",
        )
        self.request_payload = {
            "dte": {
                "identificacion": {
                    "codigoGeneracion": "4F92B17B-1D7D-4D3F-9C29-6B0F830B1E4C",
                    "numeroControl": "DTE-01-M001P001-000000000000101",
                    "tipoDte": "01",
                    "fecEmi": "2024-01-01",
                    "ambiente": "01",
                },
                "resumen": {"totalIva": "1.00"},
            }
        }

    @patch("api.dte_invalidation_service.requests.post")
    def test_invalidate_sets_fallbacks_without_staff_user(self, mock_post):
        mock_post.return_value = DummyResponse(
            {
                "success": True,
                "respuesta_hacienda": {"estado": "RECIBIDO", "descripcionMsg": "RECIBIDO"},
            }
        )
        record = DTERecord.objects.create(
            invoice=self.invoice,
            dte_type="CF",
            status="ACEPTADO",
            control_number="DTE-01-M001P001-000000000000101",
            hacienda_uuid="4F92B17B-1D7D-4D3F-9C29-6B0F830B1E4C",
            request_payload=self.request_payload,
            response_payload={
                "success": True,
                "respuesta_hacienda": {"estado": "RECIBIDO", "selloRecibido": "SELLO"},
            },
        )

        invalidation, _ = invalidate_dte_for_invoice(
            self.invoice,
            staff_user=None,
            tipo_anulacion=1,
            motivo_anulacion=None,
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.dte_status, Invoice.INVALIDATED)
        self.assertEqual(invalidation.dte_record_id, record.id)
        self.assertTrue(invalidation.solicita_nombre)
        self.assertTrue(invalidation.solicita_tipo_doc)
        self.assertTrue(invalidation.solicita_num_doc)
        self.assertTrue(invalidation.responsable_nombre)
        self.assertTrue(invalidation.responsable_tipo_doc)
        self.assertTrue(invalidation.responsable_num_doc)

    def test_invalidate_requires_sello_recibido(self):
        DTERecord.objects.create(
            invoice=self.invoice,
            dte_type="CF",
            status="ACEPTADO",
            control_number="DTE-01-M001P001-000000000000101",
            hacienda_uuid="4F92B17B-1D7D-4D3F-9C29-6B0F830B1E4C",
            request_payload=self.request_payload,
            response_payload={"success": True, "respuesta_hacienda": {"estado": "RECIBIDO"}},
        )

        api_client = APIClient()
        response = api_client.post(
            "/api/dte/invalidate/",
            {"invoice_id": self.invoice.id, "tipo_anulacion": 1},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["ok"])
