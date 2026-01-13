from unittest.mock import patch, Mock

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.connectivity import ConnectivitySentinel
from api.dte_cf_service import (
    autoresend_pending_invoices,
    send_cf_dte_for_invoice,
    transmit_invoice_dte,
)
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

    @patch("api.serializers.transmit_invoice_dte")
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


class DteAutoresendPipelineTests(TestCase):
    def setUp(self):
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

    def _create_invoice(self, status: str, with_identifiers: bool = True) -> Invoice:
        invoice = Invoice.objects.create(
            number=f"INV-{status}",
            date=timezone.now().date(),
            client=self.client_obj,
            doc_type=Invoice.CF,
            payment_method=Invoice.CASH,
            dte_status=status,
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
        if with_identifiers:
            invoice.numero_control = "DTE-01-M002P001-000000000000123"
            invoice.codigo_generacion = "ABC-123"
            invoice.save(update_fields=["numero_control", "codigo_generacion"])
        return invoice

    @patch("api.dte_cf_service.transmit_invoice_dte")
    def test_autoresend_uses_same_pipeline_as_manual_resend(self, mock_transmit):
        invoice = self._create_invoice(Invoice.PENDING)

        autoresend_pending_invoices()

        mock_transmit.assert_called_once()
        called_invoice = mock_transmit.call_args.args[0]
        self.assertEqual(called_invoice.id, invoice.id)
        self.assertEqual(mock_transmit.call_args.kwargs["force_now_timestamp"], True)
        self.assertEqual(mock_transmit.call_args.kwargs["allow_generate_identifiers"], True)
        self.assertEqual(mock_transmit.call_args.kwargs["source"], "auto_resend")

    @patch("api.dte_cf_service.transmit_invoice_dte")
    def test_autoresend_does_not_send_accepted_or_rejected(self, mock_transmit):
        self._create_invoice(Invoice.APPROVED)
        self._create_invoice(Invoice.REJECTED)

        autoresend_pending_invoices()

        mock_transmit.assert_not_called()

    @patch("api.dte_cf_service.print")
    @patch("api.dte_cf_service.requests.post")
    def test_autoresend_prints_payload(self, mock_post, mock_print):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "success": True,
            "uuid": "UUID-123",
            "respuesta_hacienda": {"estado": "RECIBIDO", "descripcionMsg": "RECIBIDO"},
        }
        mock_post.return_value = mock_response

        self._create_invoice(Invoice.PENDING, with_identifiers=False)

        autoresend_pending_invoices()

        mock_print.assert_any_call("\nJSON DTE ENVIO:\n")

    @patch("api.dte_cf_service.requests.post")
    def test_resend_keeps_identifiers_and_updates_timestamp(self, mock_post):
        mock_response = Mock(status_code=200)
        mock_response.json.return_value = {
            "success": True,
            "uuid": "UUID-123",
            "respuesta_hacienda": {"estado": "RECIBIDO", "descripcionMsg": "RECIBIDO"},
        }
        mock_post.return_value = mock_response

        invoice = self._create_invoice(Invoice.PENDING)
        fixed_now = timezone.datetime(2024, 5, 5, 15, 30, 0, tzinfo=timezone.get_current_timezone())
        with patch("api.dte_cf_service.timezone.localtime", return_value=fixed_now):
            result = transmit_invoice_dte(
                invoice,
                force_now_timestamp=True,
                allow_generate_identifiers=True,
                source="manual_resend",
            )

        self.assertTrue(result.record)
        ident = result.record.request_payload["dte"]["identificacion"]
        self.assertEqual(ident["numeroControl"], invoice.numero_control)
        self.assertEqual(ident["codigoGeneracion"], invoice.codigo_generacion)
        self.assertEqual(ident["fecEmi"], fixed_now.date().isoformat())
        self.assertEqual(ident["horEmi"], fixed_now.strftime("%H:%M:%S"))
