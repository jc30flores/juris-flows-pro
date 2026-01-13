import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import Tuple

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .connectivity import get_connectivity_status as _connectivity_status_snapshot
from .models import Activity, DTEControlCounter, DTERecord, Invoice, InvoiceItem, Service

logger = logging.getLogger(__name__)


IVA_RATE = Decimal("0.13")
ONE = Decimal("1")
CONTROL_NUMBER_WIDTH = 15
OFFLINE_USER_MESSAGE = (
    "Hacienda no disponible. DTE pendiente; se enviará automáticamente."
)


def _round_2(value: Decimal) -> Decimal:
    """
    Redondea a 2 decimales usando ROUND_HALF_UP
    (si el tercer decimal es >=5, se sube el segundo).
    """

    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def split_gross_amount_with_tax(gross) -> tuple[Decimal, Decimal]:
    """
    Recibe un monto con IVA incluido (gross) y devuelve (base, iva)
    cumpliendo:
    - iva = (gross / 1.13) * 0.13, redondeado a 2 decimales con ROUND_HALF_UP
    - base = gross - iva
    - base + iva == gross
    """

    gross_dec = Decimal(str(gross))
    base_unrounded = gross_dec / (ONE + IVA_RATE)
    iva_unrounded = base_unrounded * IVA_RATE
    iva = _round_2(iva_unrounded)
    base = gross_dec - iva
    return base, iva


def get_connectivity_status():
    return _connectivity_status_snapshot()


DTE_ENDPOINTS = {
    "CF": "https://p12101304761012.cheros.dev/api/v1/dte/factura",
    "CCF": "https://p12101304761012.cheros.dev/api/v1/dte/credito-fiscal",
    "SE": "https://p12101304761012.cheros.dev/api/v1/dte/sujeto-excluido",
}


def check_hacienda_online(timeout: int = 5) -> bool:
    health_url = getattr(settings, "HACIENDA_HEALTH_URL", None) or getattr(
        settings, "API_HEALTH_URL", None
    )
    if not health_url:
        health_url = DTE_ENDPOINTS["CF"]
    try:
        response = requests.get(health_url, timeout=timeout)
    except requests.RequestException:  # pragma: no cover - external IO
        return False
    return response.status_code == 200


def _resolve_dte_endpoint(dte_type: str) -> str:
    endpoint = DTE_ENDPOINTS.get(dte_type)
    if not endpoint:
        raise ValueError(f"Tipo de DTE no soportado para reenvío: {dte_type}")
    return endpoint


def _extract_dte_identification(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("dte"), dict):
        return payload["dte"].get("identificacion") or {}
    return payload.get("identificacion") or {}


def _send_new_dte_for_invoice(invoice) -> DTERecord:
    if invoice.doc_type == Invoice.CF:
        return send_cf_dte_for_invoice(invoice)
    if invoice.doc_type == Invoice.CCF:
        return send_ccf_dte_for_invoice(invoice)
    if invoice.doc_type == Invoice.SX:
        return send_se_dte_for_invoice(invoice)
    raise ValueError("Tipo de DTE no soportado para envío.")


def _infer_send_success(record: DTERecord) -> bool:
    response = record.response_payload or {}
    if isinstance(response, dict):
        success = response.get("success", None)
        if success is False or success is None:
            return False
    return True


def _ensure_invoice_dte_identifiers(
    invoice,
    tipo_dte: str,
    now_local: timezone.datetime,
    *,
    allow_generate_identifiers: bool = True,
) -> tuple[str, str, int | None]:
    codigo_generacion = getattr(invoice, "codigo_generacion", None) or ""
    numero_control = getattr(invoice, "numero_control", None) or ""
    control_number_value = None

    if not codigo_generacion and not allow_generate_identifiers:
        raise ValueError("Invoice sin codigo_generacion.")
    if not codigo_generacion:
        codigo_generacion = str(uuid.uuid4()).upper()

    if not numero_control and not allow_generate_identifiers:
        raise ValueError("Invoice sin numero_control.")
    if not numero_control:
        ambiente = "01"
        est_code = EMITTER_INFO["codEstable"]
        pv_code = EMITTER_INFO["codPuntoVenta"]
        numero_control, control_number_value = _build_numero_control(
            ambiente,
            tipo_dte,
            now_local.date(),
            est_code,
            pv_code,
        )

    update_fields = []
    if codigo_generacion != getattr(invoice, "codigo_generacion", None):
        invoice.codigo_generacion = codigo_generacion
        update_fields.append("codigo_generacion")
    if numero_control != getattr(invoice, "numero_control", None):
        invoice.numero_control = numero_control
        update_fields.append("numero_control")

    if update_fields:
        invoice.save(update_fields=update_fields)

    return codigo_generacion, numero_control, control_number_value


def _is_offline_status(status_code: int | None) -> bool:
    if status_code is None:
        return False
    return status_code >= 500 or status_code == 530


def _mark_invoice_attempt(
    invoice,
    now_local: timezone.datetime,
    status: str,
    error_message: str | None = None,
    error_code: str | None = None,
) -> None:
    invoice.dte_status = status
    invoice.last_dte_sent_at = now_local
    invoice.dte_send_attempts = (invoice.dte_send_attempts or 0) + 1
    invoice.last_dte_error = error_message
    invoice.last_dte_error_code = error_code
    update_fields = [
        "dte_status",
        "last_dte_sent_at",
        "dte_send_attempts",
        "last_dte_error",
        "last_dte_error_code",
    ]
    invoice.save(update_fields=update_fields)


def _mark_invoice_offline(invoice, now_local: timezone.datetime, error: str, code: str) -> None:
    _mark_invoice_attempt(
        invoice,
        now_local,
        Invoice.PENDING,
        error_message=error,
        error_code=code,
    )
    invoice._dte_message = OFFLINE_USER_MESSAGE
    invoice._dte_pending_due_to_outage = True


@dataclass(frozen=True)
class DteTransmitResult:
    ok: bool
    status: str
    message: str
    record: DTERecord | None
    response_payload: dict | None
    sent_at: timezone.datetime
    did_generate_new_dte: bool


def transmit_invoice_dte(
    invoice,
    *,
    force_now_timestamp: bool,
    allow_generate_identifiers: bool,
    source: str,
) -> DteTransmitResult:
    now_local = timezone.localtime(timezone.now())
    had_existing_record = invoice.dte_records.exists()

    if source in {"manual_resend", "auto_resend"} and invoice.dte_status != Invoice.PENDING:
        message = "Solo se puede reenviar un DTE en estado PENDIENTE."
        logger.warning(
            "Skipping DTE transmit for invoice %s (%s). Status=%s",
            invoice.id,
            source,
            invoice.dte_status,
        )
        return DteTransmitResult(
            ok=False,
            status=invoice.dte_status,
            message=message,
            record=None,
            response_payload=None,
            sent_at=now_local,
            did_generate_new_dte=not had_existing_record,
        )

    if not invoice.items.exists():
        message = "No se encontraron items para generar el DTE."
        logger.error("Invoice %s has no items for DTE send.", invoice.id)
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=message,
            error_code="no_items",
        )
        return DteTransmitResult(
            ok=False,
            status=invoice.dte_status,
            message=message,
            record=None,
            response_payload=None,
            sent_at=now_local,
            did_generate_new_dte=not had_existing_record,
        )

    if not allow_generate_identifiers and (
        not getattr(invoice, "codigo_generacion", None)
        or not getattr(invoice, "numero_control", None)
    ):
        message = "Factura pendiente sin identificadores DTE."
        logger.error("Invoice %s missing DTE identifiers.", invoice.id)
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=message,
            error_code="missing_identifiers",
        )
        return DteTransmitResult(
            ok=False,
            status=invoice.dte_status,
            message=message,
            record=None,
            response_payload=None,
            sent_at=now_local,
            did_generate_new_dte=not had_existing_record,
        )

    try:
        if invoice.doc_type == Invoice.CF:
            record = send_cf_dte_for_invoice(
                invoice,
                force_now_timestamp=force_now_timestamp,
                allow_generate_identifiers=allow_generate_identifiers,
                source=source,
            )
        elif invoice.doc_type == Invoice.CCF:
            record = send_ccf_dte_for_invoice(
                invoice,
                force_now_timestamp=force_now_timestamp,
                allow_generate_identifiers=allow_generate_identifiers,
                source=source,
            )
        elif invoice.doc_type == Invoice.SX:
            record = send_se_dte_for_invoice(
                invoice,
                force_now_timestamp=force_now_timestamp,
                allow_generate_identifiers=allow_generate_identifiers,
                source=source,
            )
        else:
            raise ValueError("Tipo de DTE no soportado para envío.")
    except ValueError as exc:
        logger.exception("Invalid DTE transmit for invoice %s", invoice.id, exc_info=exc)
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=str(exc),
            error_code="invalid_payload",
        )
        return DteTransmitResult(
            ok=False,
            status=invoice.dte_status,
            message=str(exc),
            record=None,
            response_payload=None,
            sent_at=now_local,
            did_generate_new_dte=not had_existing_record,
        )

    message = getattr(invoice, "_dte_message", "") or ""
    return DteTransmitResult(
        ok=_infer_send_success(record),
        status=invoice.dte_status,
        message=message,
        record=record,
        response_payload=record.response_payload,
        sent_at=now_local,
        did_generate_new_dte=not had_existing_record,
    )


def resend_dte_for_invoice(
    invoice,
) -> tuple[DTERecord, str, timezone.datetime, bool, bool]:
    result = transmit_invoice_dte(
        invoice,
        force_now_timestamp=True,
        allow_generate_identifiers=True,
        source="manual_resend",
    )
    return (
        result.record,
        result.message,
        result.sent_at,
        result.ok,
        result.did_generate_new_dte,
    )


def autoresend_pending_invoices() -> int:
    pending_ids: list[int] = []
    with transaction.atomic():
        pending_ids = list(
            Invoice.objects.select_for_update(skip_locked=True)
            .filter(
                dte_status=Invoice.PENDING,
                codigo_generacion__isnull=False,
                numero_control__isnull=False,
            )
            .values_list("id", flat=True)
        )

    if not pending_ids:
        return 0

    sent = 0
    for invoice_id in pending_ids:
        invoice = (
            Invoice.objects.select_related("client")
            .prefetch_related("items", "dte_records")
            .get(pk=invoice_id)
        )
        try:
            transmit_invoice_dte(
                invoice,
                force_now_timestamp=True,
                allow_generate_identifiers=True,
                source="auto_resend",
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error auto-resending DTE for invoice %s", invoice_id, exc_info=exc
            )
            continue
    return sent


def _build_numero_control(
    ambiente: str,
    tipo_dte: str,
    emision_date,
    est_code: str,
    pv_code: str,
) -> tuple[str, int]:
    with transaction.atomic():
        counter, _ = DTEControlCounter.objects.select_for_update().get_or_create(
            ambiente=ambiente,
            tipo_dte=tipo_dte,
            anio_emision=emision_date.year,
            est_code=est_code,
            pv_code=pv_code,
        )
        next_number = counter.last_number + 1
    correlativo = str(next_number).zfill(CONTROL_NUMBER_WIDTH)
    return f"DTE-{tipo_dte}-{est_code}{pv_code}-{correlativo}", next_number


def _mark_control_number_processed(
    ambiente: str,
    tipo_dte: str,
    emision_date,
    est_code: str,
    pv_code: str,
    processed_number: int,
) -> None:
    with transaction.atomic():
        counter, _ = DTEControlCounter.objects.select_for_update().get_or_create(
            ambiente=ambiente,
            tipo_dte=tipo_dte,
            anio_emision=emision_date.year,
            est_code=est_code,
            pv_code=pv_code,
        )
        if processed_number > counter.last_number:
            counter.last_number = processed_number
            counter.save(update_fields=["last_number"])


UNIDADES = [
    "CERO",
    "UNO",
    "DOS",
    "TRES",
    "CUATRO",
    "CINCO",
    "SEIS",
    "SIETE",
    "OCHO",
    "NUEVE",
    "DIEZ",
    "ONCE",
    "DOCE",
    "TRECE",
    "CATORCE",
    "QUINCE",
    "DIECISÉIS",
    "DIECISIETE",
    "DIECIOCHO",
    "DIECINUEVE",
    "VEINTE",
]

DECENAS = [
    "",
    "",
    "VEINTE",
    "TREINTA",
    "CUARENTA",
    "CINCUENTA",
    "SESENTA",
    "SETENTA",
    "OCHENTA",
    "NOVENTA",
]

CENTENAS = [
    "",
    "CIENTO",
    "DOSCIENTOS",
    "TRESCIENTOS",
    "CUATROCIENTOS",
    "QUINIENTOS",
    "SEISCIENTOS",
    "SETECIENTOS",
    "OCHOCIENTOS",
    "NOVECIENTOS",
]


def _number_to_words_0_99(n: int) -> str:
    if n <= 20:
        return UNIDADES[n]
    if n < 30:
        return "VEINTI" + UNIDADES[n - 20].lower().upper()
    d, u = divmod(n, 10)
    if u == 0:
        return DECENAS[d]
    return f"{DECENAS[d]} Y {UNIDADES[u]}"


def _number_to_words_0_999(n: int) -> str:
    if n == 0:
        return "CERO"
    if n == 100:
        return "CIEN"
    c, r = divmod(n, 100)
    if c == 0:
        return _number_to_words_0_99(r)
    if r == 0:
        return CENTENAS[c]
    return f"{CENTENAS[c]} {_number_to_words_0_99(r)}"


def _number_to_words(n: int) -> str:
    if n == 0:
        return "CERO"
    if n < 1000:
        return _number_to_words_0_999(n)
    miles, resto = divmod(n, 1000)
    prefix = "MIL" if miles == 1 else f"{_number_to_words_0_999(miles)} MIL"
    if resto == 0:
        return prefix
    return f"{prefix} {_number_to_words_0_999(resto)}"


def amount_to_spanish_words(amount) -> str:
    dec = _round_2(Decimal(str(amount)))
    enteros = int(dec)
    centavos = int((dec - Decimal(enteros)) * 100)

    palabras_enteros = _number_to_words(enteros)
    moneda = "DOLAR" if enteros == 1 else "DOLARES"

    if centavos == 0:
        return f"{palabras_enteros} {moneda}"

    centavos_str = f"{centavos:02d}"
    return f"{palabras_enteros} {moneda} CON {centavos_str} CENTAVOS"


def interpret_dte_response(response_data: dict) -> Tuple[str, str, str]:
    """
    Retorna (estado_interno, estado_hacienda, mensaje_usuario):
      - estado_interno: "ACEPTADO" | "RECHAZADO" | "PENDIENTE"
      - estado_hacienda: string devuelto por Hacienda (o "SIN_RESPUESTA")
      - mensaje_usuario: mensaje para mostrar en frontend
    """
    success = response_data.get("success", None)

    # Caso de rechazo explícito de Hacienda (success = false)
    if success is False:
        error = response_data.get("error") or {}
        hresp = error.get("respuesta_hacienda") or error.get("hacienda_response") or {}
        estado_h = hresp.get("estado", "RECHAZADO")
        desc = hresp.get("descripcionMsg") or error.get("message") or "El DTE fue rechazado por Hacienda."
        msg = f"Hacienda rechazó el DTE: {desc}"
        return "RECHAZADO", estado_h, msg

    # Caso de éxito (success = true)
    if success is True:
        hresp = response_data.get("respuesta_hacienda") or response_data.get("hacienda_response") or {}
        estado_h = hresp.get("estado", "")
        desc = hresp.get("descripcionMsg", "")

        # ACEPTADO: estado PROCESADO/RECIBIDO (Documento procesado exitosamente)
        if estado_h in ("PROCESADO", "RECIBIDO") or desc.upper().strip() == "RECIBIDO":
            msg = "DTE aceptado por Hacienda (RECIBIDO)."
            return "ACEPTADO", estado_h or "RECIBIDO", msg

        # Cualquier otro estado con success=true → dejamos PENDIENTE
        msg = f"DTE enviado, en espera de confirmación de Hacienda (estado='{estado_h or 'DESCONOCIDO'}')."
        return "PENDIENTE", estado_h or "DESCONOCIDO", msg

    # Cualquier otro caso (sin campo success, HTML, etc.) → PENDIENTE
    return "PENDIENTE", "SIN_RESPUESTA", "DTE en estado PENDIENTE: la respuesta de la API no se pudo interpretar."


EMITTER_INFO = {
    "nit": "12101304761012",
    "nrc": "1880600",
    "nombre": "MIRNA ABIGAIL GARCIA FLORES",
    "nombreComercial": "Oficina Juridica Garcia Flores",
    "codActividad": "69100",
    "descActividad": "Actividades juridicas",
    "direccion": {
        "municipio": "22",
        "complemento": "24 Calle oriente, col. lopez, #13,san miguel, san miguel",
        "departamento": "12",
    },
    "telefono": "50376523555",
    "correo": "dtemirnagarcia@gmail.com",
    "codEstable": "M002",
    "codPuntoVenta": "P001",
    "codPuntoVentaMH": "P001",
    "codEstableMH": "M002",
    "tipoEstablecimiento": "02",
}


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_currency(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _build_receptor(invoice):
    client = getattr(invoice, "client", None)
    emitter_address = EMITTER_INFO["direccion"]
    if not client:
        return {
            "correo": None,
            "nombre": "VENTA AL PUBLICO",
            "tipoDocumento": "13",
            "direccion": emitter_address,
            "numDocumento": "00000000-0",
            "nrc": None,
            "telefono": "00000000",
            "codActividad": None,
            "descActividad": None,
        }, "00000000-0", "VENTA AL PUBLICO"

    receiver_name = client.company_name or client.full_name or "VENTA AL PUBLICO"
    receiver_document = client.nit or client.dui or "00000000-0"
    receiver_phone = client.phone or "00000000"
    receiver_email = client.email or None
    receiver_address = {
        "municipio": client.municipality_code or emitter_address.get("municipio", "22"),
        "complemento": emitter_address.get("complemento", ""),
        "departamento": client.department_code or emitter_address.get("departamento", "12"),
    }

    receptor_payload = {
        "correo": receiver_email,
        "nombre": receiver_name,
        "tipoDocumento": "13",
        "direccion": receiver_address,
        "numDocumento": receiver_document,
        "nrc": None,
        "telefono": receiver_phone,
        "codActividad": None,
        "descActividad": None,
    }

    return receptor_payload, receiver_document, receiver_name


def _resolve_receiver_doc_for_extension(client, context_label: str) -> str:
    default_doc = "00000000-0"

    if client is None:
        logger.warning(
            "No receiver client for %s. Using fallback docuRecibe=%s.",
            context_label,
            default_doc,
        )
        return default_doc

    receiver_nit = (getattr(client, "nit", "") or "").strip()
    if receiver_nit:
        return receiver_nit

    receiver_dui = (getattr(client, "dui", "") or "").strip()
    if receiver_dui:
        return receiver_dui

    logger.warning(
        "No valid receiver document for %s (client_id=%s). Using fallback docuRecibe=%s.",
        context_label,
        client.id,
        default_doc,
    )
    return default_doc


def send_cf_dte_for_invoice(
    invoice,
    *,
    force_now_timestamp: bool = False,
    allow_generate_identifiers: bool = True,
    source: str = "normal_send",
) -> DTERecord:
    """
    Construye el JSON DTE para tipo CF a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    now_local = timezone.localtime()
    codigo_generacion, numero_control, control_number_value = _ensure_invoice_dte_identifiers(
        invoice,
        "01",
        now_local,
        allow_generate_identifiers=allow_generate_identifiers,
    )
    ambiente = "01"
    est_code = EMITTER_INFO["codEstable"]
    pv_code = EMITTER_INFO["codPuntoVenta"]

    emision_date = now_local.date()
    fec_emi = emision_date.isoformat()
    hor_emi = now_local.strftime("%H:%M:%S")

    receptor, receiver_nit, receiver_name = _build_receptor(invoice)
    receiver_doc_for_extension = _resolve_receiver_doc_for_extension(
        getattr(invoice, "client", None),
        f"CF invoice {invoice.id}",
    )
    items: list[InvoiceItem] = list(invoice.items.select_related("service"))

    cuerpo_documento = []
    total_base = Decimal("0.00")
    total_iva = Decimal("0.00")
    total_gross = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        unit_price = Decimal(str(item.unit_price))
        quantity = Decimal(str(item.quantity))
        gross_line = quantity * unit_price

        base_line, iva_line = split_gross_amount_with_tax(gross_line)

        total_base += base_line
        total_iva += iva_line
        total_gross += gross_line

        service: Service | None = getattr(item, "service", None)
        descripcion = service.name if service else "Servicio"
        codigo = service.code if service and service.code else "SERV"

        cuerpo_documento.append(
            {
                "ventaExenta": 0,
                "uniMedida": 59,
                "cantidad": float(quantity),
                "noGravado": 0,
                "ivaItem": float(_round_2(iva_line)),
                "numeroDocumento": None,
                "codigo": codigo,
                "ventaGravada": float(_round_2(gross_line)),
                "codTributo": None,
                "numItem": index,
                "psv": 0,
                "ventaNoSuj": 0,
                "precioUni": float(_round_2(unit_price)),
                "montoDescu": 0,
                "tributos": None,
                "descripcion": descripcion,
                "tipoItem": 1,
            }
        )

    total_base = _round_2(total_base)
    total_iva = _round_2(total_iva)
    total_gross = _round_2(total_gross)
    monto_total_operacion = total_gross
    total_pagar = total_gross

    resumen = {
        "totalDescu": 0,
        "ivaRete1": 0,
        "pagos": [
            {
                "plazo": None,
                "periodo": None,
                "codigo": "01",
                "referencia": None,
                "montoPago": float(total_pagar),
            }
        ],
        "porcentajeDescuento": 0,
        "saldoFavor": 0,
        "totalNoGravado": 0,
        "totalGravada": float(total_gross),
        "descuExenta": 0,
        "subTotal": float(total_gross),
        "totalLetras": amount_to_spanish_words(total_gross),
        "descuNoSuj": 0,
        "subTotalVentas": float(total_gross),
        "reteRenta": 0,
        "tributos": None,
        "totalNoSuj": 0,
        "montoTotalOperacion": float(monto_total_operacion),
        "totalIva": float(total_iva),
        "descuGravada": 0,
        "totalExenta": 0,
        "condicionOperacion": 1,
        "totalPagar": float(total_pagar),
        "numPagoElectronico": None,
    }

    observaciones = invoice.observations.strip() if invoice.observations else ""
    if not observaciones:
        observaciones = "Venta al mostrador"

    payload = {
        "dte": {
            "apendice": None,
            "identificacion": {
                "codigoGeneracion": codigo_generacion,
                "motivoContin": None,
                "fecEmi": fec_emi,
                "tipoModelo": 1,
                "tipoDte": "01",
                "version": 1,
                "tipoContingencia": None,
                "ambiente": ambiente,
                "numeroControl": numero_control,
                "horEmi": hor_emi,
                "tipoOperacion": 1,
                "tipoMoneda": "USD",
            },
            "resumen": resumen,
            "extension": {
                "observaciones": observaciones,
                "placaVehiculo": None,
                "docuRecibe": receiver_doc_for_extension,
                "nombEntrega": None,
                "nombRecibe": None,
                "docuEntrega": None,
            },
            "cuerpoDocumento": cuerpo_documento,
            "emisor": {
                **EMITTER_INFO,
            },
            "documentoRelacionado": None,
            "ventaTercero": None,
            "otrosDocumentos": None,
            "receptor": receptor,
        }
    }

    url = "https://p12101304761012.cheros.dev/api/v1/dte/factura"

    print(f'\nENDPOINT DTE: "{url}"\n')
    print("\nJSON DTE ENVIO:\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    record = DTERecord.objects.create(
        invoice=invoice,
        dte_type="CF",
        status="ENVIANDO",
        control_number=numero_control,
        issuer_nit=EMITTER_INFO["nit"],
        receiver_nit=receiver_nit,
        receiver_name=receiver_name,
        issue_date=invoice.date,
        total_amount=invoice.total,
        request_payload=payload,
    )
    headers = {
        "Authorization": "Bearer api_k_12101304761012",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.exceptions.RequestException as exc:
        print("Error sending DTE:", exc)

        record.response_payload = {
            "success": None,
            "error": {
                "type": "network_error",
                "message": str(exc),
            },
        }
        record.hacienda_state = "SIN_RESPUESTA"
        record.status = "PENDIENTE"
        record.save(update_fields=["response_payload", "hacienda_state", "status"])

        _mark_invoice_offline(invoice, now_local, str(exc), "network_error")

        return record

    try:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        if _is_offline_status(response.status_code):
            record.response_payload = {
                "status_code": response.status_code,
                "raw_text": response.text,
            }
            record.hacienda_state = "SIN_RESPUESTA"
            record.status = "PENDIENTE"
            record.save(update_fields=["response_payload", "hacienda_state", "status"])
            _mark_invoice_offline(
                invoice,
                now_local,
                f"status_{response.status_code}",
                str(response.status_code),
            )
            return record

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        estado_interno, estado_hacienda, user_message = interpret_dte_response(response_data)
        record.hacienda_state = estado_hacienda
        record.status = estado_interno
        record.save(update_fields=["response_payload", "hacienda_uuid", "hacienda_state", "status"])

        if estado_hacienda == "PROCESADO":
            _mark_control_number_processed(
                ambiente,
                "01",
                emision_date,
                est_code,
                pv_code,
                control_number_value or 0,
            )

        _mark_invoice_attempt(invoice, now_local, estado_interno, None, None)
        invoice._dte_message = user_message
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending CF DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "PENDIENTE"
        record.hacienda_state = "SIN_RESPUESTA"
        record.save(update_fields=["response_payload", "status", "hacienda_state"])
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=str(exc),
            error_code="unexpected_error",
        )
        invoice._dte_message = "El DTE se ha dejado en estado PENDIENTE por un error inesperado."
        return record


def send_ccf_dte_for_invoice(
    invoice,
    *,
    force_now_timestamp: bool = False,
    allow_generate_identifiers: bool = True,
    source: str = "normal_send",
) -> DTERecord:
    """
    Construye el JSON DTE para tipo CCF (03) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    now_local = timezone.localtime()
    codigo_generacion, numero_control, control_number_value = _ensure_invoice_dte_identifiers(
        invoice,
        "03",
        now_local,
        allow_generate_identifiers=allow_generate_identifiers,
    )
    ambiente = "01"
    est_code = EMITTER_INFO["codEstable"]
    pv_code = EMITTER_INFO["codPuntoVenta"]

    emision_date = now_local.date()
    fec_emi = emision_date.isoformat()
    hor_emi = now_local.strftime("%H:%M:%S")

    client = getattr(invoice, "client", None)
    emitter_address = EMITTER_INFO["direccion"]

    client_name = (client.company_name if client else "") or (client.full_name if client else "") or "CLIENTE"
    client_trade_name = client.company_name if client and client.company_name else client_name
    client_nit = (client.nit if client else "") or ""
    raw_nrc = getattr(client, "nrc", "") or ""
    client_nrc_digits = "".join(ch for ch in raw_nrc if str(ch).isdigit())
    client_nrc = (
        client_nrc_digits if 6 <= len(client_nrc_digits) <= 8 else None
    )
    client_phone = (client.phone if client else "") or "00000000"
    client_email = (client.email if client else "") or None
    client_cod_act = getattr(client, "activity_code", None) or None
    client_desc_act = getattr(client, "activity_description", None) or None

    if not client_desc_act and client_cod_act:
        act = Activity.objects.filter(code=client_cod_act).first()
        if act:
            client_desc_act = act.description

    client_address = {
        "municipio": (client.municipality_code if client else None)
        or emitter_address.get("municipio", "22"),
        "complemento": (getattr(client, "direccion", None) or "")
        or emitter_address.get("complemento", ""),
        "departamento": (client.department_code if client else None)
        or emitter_address.get("departamento", "12"),
    }

    receptor = {
        "nombre": client_name,
        "nombreComercial": client_trade_name,
        "direccion": client_address,
        "correo": client_email,
        "nit": client_nit,
        "telefono": client_phone,
    }

    if client_nrc:
        receptor["nrc"] = client_nrc
    if client_cod_act:
        receptor["codActividad"] = client_cod_act
    if client_desc_act:
        receptor["descActividad"] = client_desc_act
    elif client_cod_act:
        receptor["descActividad"] = "Actividad no especificada"

    receiver_doc_for_extension = _resolve_receiver_doc_for_extension(
        client,
        f"CCF invoice {invoice.id}",
    )

    items: list[InvoiceItem] = list(invoice.items.select_related("service"))
    cuerpo_documento = []
    total_gross = Decimal("0.00")
    total_base = Decimal("0.00")
    total_iva = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        gross_unit = Decimal(str(item.unit_price))
        qty_dec = Decimal(str(item.quantity))
        gross_line = gross_unit * qty_dec
        line_base, iva_line = split_gross_amount_with_tax(gross_line)

        total_gross += gross_line
        total_base += line_base
        total_iva += iva_line

        service: Service | None = getattr(item, "service", None)
        descripcion = service.name if service else "Servicio"
        codigo = service.code if service and service.code else "SERVICIO"

        precio_base_unitario = _round_2(line_base / qty_dec) if qty_dec else _round_2(Decimal("0"))

        cuerpo_documento.append(
            {
                "ventaExenta": 0,
                "numItem": index,
                "tipoItem": 1,
                "codigo": codigo,
                "cantidad": float(qty_dec),
                "tributos": ["20"],
                "uniMedida": 59,
                "noGravado": 0,
                "codTributo": None,
                "montoDescu": 0,
                "ventaNoSuj": 0,
                "psv": 0,
                "precioUni": float(precio_base_unitario),
                "descripcion": descripcion,
                "ventaGravada": float(_round_2(line_base)),
                "numeroDocumento": None,
            }
        )

    total_gross = _round_2(total_gross)
    total_base = _round_2(total_base)
    total_iva = _round_2(total_iva)
    total_operacion = _round_2(total_gross)
    total_letras = amount_to_spanish_words(total_operacion)

    resumen = {
        "totalDescu": 0,
        "ivaRete1": 0,
        "pagos": [
            {
                "plazo": None,
                "periodo": None,
                "codigo": "01",
                "referencia": None,
                "montoPago": float(total_operacion),
            }
        ],
        "porcentajeDescuento": 0,
        "saldoFavor": 0,
        "totalNoGravado": 0,
        "totalGravada": float(total_base),
        "descuExenta": 0,
        "subTotal": float(total_base),
        "totalLetras": total_letras,
        "descuNoSuj": 0,
        "subTotalVentas": float(total_base),
        "reteRenta": 0,
        "tributos": [
            {
                "valor": float(total_iva),
                "descripcion": "Impuesto al Valor Agregado 13%",
                "codigo": "20",
            }
        ],
        "totalNoSuj": 0,
        "montoTotalOperacion": float(total_operacion),
        "descuGravada": 0,
        "totalExenta": 0,
        "condicionOperacion": 1,
        "totalPagar": float(total_operacion),
        "ivaPerci1": 0,
        "numPagoElectronico": None,
    }

    observaciones = invoice.observations.strip() if invoice.observations else ""
    if not observaciones:
        observaciones = "Crédito fiscal para deducción fiscal del cliente"

    payload = {
        "dte": {
            "apendice": None,
            "identificacion": {
                "codigoGeneracion": codigo_generacion,
                "motivoContin": None,
                "fecEmi": fec_emi,
                "tipoModelo": 1,
                "tipoDte": "03",
                "version": 3,
                "tipoContingencia": None,
                "ambiente": ambiente,
                "numeroControl": numero_control,
                "horEmi": hor_emi,
                "tipoOperacion": 1,
                "tipoMoneda": "USD",
            },
            "resumen": resumen,
            "extension": {
                "observaciones": observaciones,
                "placaVehiculo": None,
                "docuRecibe": receiver_doc_for_extension,
                "nombEntrega": None,
                "nombRecibe": None,
                "docuEntrega": None,
            },
            "cuerpoDocumento": cuerpo_documento,
            "emisor": {**EMITTER_INFO},
            "documentoRelacionado": None,
            "ventaTercero": None,
            "otrosDocumentos": None,
            "receptor": receptor,
        }
    }

    url = "https://p12101304761012.cheros.dev/api/v1/dte/credito-fiscal"

    print(f'\nENDPOINT DTE: "{url}"\n')
    print("\nJSON DTE ENVIO:\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    record = DTERecord.objects.create(
        invoice=invoice,
        dte_type="CCF",
        status="ENVIANDO",
        control_number=numero_control,
        issuer_nit=EMITTER_INFO["nit"],
        receiver_nit=client_nit,
        receiver_name=client_name,
        issue_date=invoice.date,
        total_amount=_to_decimal(total_operacion),
        request_payload=payload,
    )
    headers = {
        "Authorization": "Bearer api_k_12101304761012",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.exceptions.RequestException as exc:
        print("Error sending DTE:", exc)

        record.response_payload = {
            "success": None,
            "error": {
                "type": "network_error",
                "message": str(exc),
            },
        }
        record.hacienda_state = "SIN_RESPUESTA"
        record.status = "PENDIENTE"
        record.save(update_fields=["response_payload", "hacienda_state", "status"])

        _mark_invoice_offline(invoice, now_local, str(exc), "network_error")

        return record

    try:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        if _is_offline_status(response.status_code):
            record.response_payload = {
                "status_code": response.status_code,
                "raw_text": response.text,
            }
            record.hacienda_state = "SIN_RESPUESTA"
            record.status = "PENDIENTE"
            record.save(update_fields=["response_payload", "hacienda_state", "status"])
            _mark_invoice_offline(
                invoice,
                now_local,
                f"status_{response.status_code}",
                str(response.status_code),
            )
            return record

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        estado_interno, estado_hacienda, user_message = interpret_dte_response(response_data)
        record.hacienda_state = estado_hacienda
        record.status = estado_interno
        record.save(update_fields=["response_payload", "hacienda_uuid", "hacienda_state", "status"])

        if estado_hacienda == "PROCESADO":
            _mark_control_number_processed(
                ambiente,
                "03",
                emision_date,
                est_code,
                pv_code,
                control_number_value or 0,
            )

        _mark_invoice_attempt(invoice, now_local, estado_interno, None, None)
        invoice._dte_message = user_message
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending CCF DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "PENDIENTE"
        record.hacienda_state = "SIN_RESPUESTA"
        record.save(update_fields=["response_payload", "status", "hacienda_state"])
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=str(exc),
            error_code="unexpected_error",
        )
        invoice._dte_message = "El DTE se ha dejado en estado PENDIENTE por un error inesperado."
        return record


def send_se_dte_for_invoice(
    invoice,
    *,
    force_now_timestamp: bool = False,
    allow_generate_identifiers: bool = True,
    source: str = "normal_send",
) -> DTERecord:
    """
    Construye el JSON DTE para tipo Sujeto Excluido (14) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    now_local = timezone.localtime()
    codigo_generacion, numero_control, control_number_value = _ensure_invoice_dte_identifiers(
        invoice,
        "14",
        now_local,
        allow_generate_identifiers=allow_generate_identifiers,
    )
    ambiente = "01"
    est_code = EMITTER_INFO["codEstable"]
    pv_code = EMITTER_INFO["codPuntoVenta"]

    emision_date = now_local.date()
    fec_emi = emision_date.isoformat()
    hor_emi = now_local.strftime("%H:%M:%S")

    client = getattr(invoice, "client", None)
    se_tipo_documento = "13"
    se_nombre = (client.company_name if client else "") or (client.full_name if client else "") or "CONSUMIDOR FINAL"
    se_telefono = (client.phone if client else None) or "00000000"
    client_dui = (getattr(client, "dui", "") or "").strip()
    client_dui_digits = "".join(ch for ch in client_dui if ch.isdigit())
    se_num_documento = client_dui_digits if len(client_dui_digits) == 9 else "000000000"
    se_correo = (getattr(client, "email", None) or None)
    se_cod_actividad = (getattr(client, "activity_code", None) or None)
    se_desc_actividad = getattr(client, "activity_description", None) or None
    se_departamento = (
        getattr(client, "department_code", None)
        or EMITTER_INFO["direccion"].get("departamento", "12")
    )
    se_municipio = (
        getattr(client, "municipality_code", None)
        or EMITTER_INFO["direccion"].get("municipio", "22")
    )
    se_direccion = getattr(client, "address", None) or EMITTER_INFO["direccion"].get(
        "complemento", "Colonia Centro, Calle Principal"
    )

    sujeto_excluido = {
        "tipoDocumento": se_tipo_documento,
        "nombre": se_nombre,
        "telefono": se_telefono,
        "descActividad": se_desc_actividad,
        "numDocumento": se_num_documento,
        "direccion": {
            "municipio": se_municipio,
            "complemento": se_direccion,
            "departamento": se_departamento,
        },
        "codActividad": se_cod_actividad,
        "correo": se_correo,
    }

    items: list[InvoiceItem] = list(invoice.items.select_related("service"))
    cuerpo_documento = []
    total_compra = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        unit_price = _to_decimal(item.unit_price)
        quantity = Decimal(item.quantity)
        line_total = _to_decimal(item.subtotal if item.subtotal else unit_price * quantity)
        total_compra += line_total

        service: Service | None = getattr(item, "service", None)
        descripcion = service.name if service else "Servicio"
        codigo = service.code if service and service.code else "SERV"

        cuerpo_documento.append(
            {
                "cantidad": float(quantity),
                "tipoItem": 1,
                "montoDescu": 0,
                "compra": _format_currency(line_total),
                "codigo": codigo,
                "descripcion": descripcion,
                "uniMedida": 59,
                "precioUni": _format_currency(unit_price),
                "numItem": index,
            }
        )

    sub_total = total_compra
    total_pagar = total_compra
    observaciones = invoice.observations.strip() if invoice.observations else ""
    if not observaciones:
        observaciones = "Venta a consumidor final - Sujeto Excluido"

    resumen = {
        "observaciones": observaciones,
        "totalDescu": 0,
        "pagos": [
            {
                "plazo": None,
                "periodo": None,
                "codigo": "01",
                "referencia": None,
                "montoPago": _format_currency(total_pagar),
            }
        ],
        "subTotal": _format_currency(sub_total),
        "descu": 0,
        "reteRenta": 0,
        "condicionOperacion": 1,
        "ivaRete1": 0,
        "totalLetras": amount_to_spanish_words(total_pagar),
        "totalCompra": _format_currency(total_compra),
        "totalPagar": _format_currency(total_pagar),
    }

    payload = {
        "dte": {
            "apendice": None,
            "cuerpoDocumento": cuerpo_documento,
            "resumen": resumen,
            "sujetoExcluido": sujeto_excluido,
            "emisor": {
                "correo": EMITTER_INFO["correo"],
                "codPuntoVenta": EMITTER_INFO["codPuntoVenta"],
                "nombre": EMITTER_INFO["nombre"],
                "codEstableMH": EMITTER_INFO["codEstableMH"],
                "direccion": EMITTER_INFO["direccion"],
                "codPuntoVentaMH": EMITTER_INFO["codPuntoVentaMH"],
                "codEstable": EMITTER_INFO["codEstable"],
                "nit": EMITTER_INFO["nit"],
                "nrc": EMITTER_INFO["nrc"],
                "telefono": EMITTER_INFO["telefono"],
                "codActividad": EMITTER_INFO["codActividad"],
                "descActividad": EMITTER_INFO["descActividad"],
            },
            "identificacion": {
                "codigoGeneracion": codigo_generacion,
                "motivoContin": None,
                "fecEmi": fec_emi,
                "tipoModelo": 1,
                "tipoDte": "14",
                "version": 1,
                "tipoContingencia": None,
                "ambiente": ambiente,
                "numeroControl": numero_control,
                "horEmi": hor_emi,
                "tipoOperacion": 1,
                "tipoMoneda": "USD",
            },
        }
    }

    url = "https://p12101304761012.cheros.dev/api/v1/dte/sujeto-excluido"

    print(f'\nENDPOINT DTE: "{url}"\n')
    print("\nJSON DTE ENVIO:\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    record = DTERecord.objects.create(
        invoice=invoice,
        dte_type="SE",
        status="ENVIANDO",
        control_number=numero_control,
        issuer_nit=EMITTER_INFO["nit"],
        receiver_nit=se_num_documento,
        receiver_name=se_nombre,
        issue_date=invoice.date,
        total_amount=_to_decimal(total_pagar),
        request_payload=payload,
    )
    headers = {
        "Authorization": "Bearer api_k_12101304761012",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.exceptions.RequestException as exc:
        print("Error sending DTE:", exc)

        record.response_payload = {
            "success": None,
            "error": {
                "type": "network_error",
                "message": str(exc),
            },
        }
        record.hacienda_state = "SIN_RESPUESTA"
        record.status = "PENDIENTE"
        record.save(update_fields=["response_payload", "hacienda_state", "status"])

        _mark_invoice_offline(invoice, now_local, str(exc), "network_error")

        return record

    try:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        if _is_offline_status(response.status_code):
            record.response_payload = {
                "status_code": response.status_code,
                "raw_text": response.text,
            }
            record.hacienda_state = "SIN_RESPUESTA"
            record.status = "PENDIENTE"
            record.save(update_fields=["response_payload", "hacienda_state", "status"])
            _mark_invoice_offline(
                invoice,
                now_local,
                f"status_{response.status_code}",
                str(response.status_code),
            )
            return record

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        estado_interno, estado_hacienda, user_message = interpret_dte_response(response_data)
        record.hacienda_state = estado_hacienda
        record.status = estado_interno
        record.save(update_fields=["response_payload", "hacienda_uuid", "hacienda_state", "status"])

        if estado_hacienda == "PROCESADO":
            _mark_control_number_processed(
                ambiente,
                "14",
                emision_date,
                est_code,
                pv_code,
                control_number_value or 0,
            )

        _mark_invoice_attempt(invoice, now_local, estado_interno, None, None)
        invoice._dte_message = user_message
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending SE DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "PENDIENTE"
        record.hacienda_state = "SIN_RESPUESTA"
        record.save(update_fields=["response_payload", "status", "hacienda_state"])
        _mark_invoice_attempt(
            invoice,
            now_local,
            Invoice.PENDING,
            error_message=str(exc),
            error_code="unexpected_error",
        )
        invoice._dte_message = "El DTE se ha dejado en estado PENDIENTE por un error inesperado."
        return record
