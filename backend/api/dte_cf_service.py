import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Tuple

import requests
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from .connectivity import get_connectivity_status as _connectivity_status_snapshot
from .models import (
    Activity,
    DTEControlCounter,
    DTERecord,
    Invoice,
    InvoiceItem,
    IssuerProfile,
    Service,
    StaffUser,
)

logger = logging.getLogger(__name__)


IVA_RATE = Decimal("0.13")
ONE = Decimal("1")
CONTROL_NUMBER_WIDTH = 15
PENDING_DTE_MESSAGE = "Hacienda no disponible. DTE pendiente; se enviará automáticamente."
DEFAULT_HACIENDA_HEALTH_URL = getattr(
    settings,
    "API_HEALTH_URL",
    "https://p12172402231026.cheros.dev/health",
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


def check_hacienda_online(url: str | None = None, timeout: int = 5) -> bool:
    target_url = url or DEFAULT_HACIENDA_HEALTH_URL
    try:
        response = requests.get(target_url, timeout=timeout)
    except requests.RequestException:
        return False
    return response.status_code == 200


def _parse_control_number_value(numero_control: str | None) -> int | None:
    if not numero_control:
        return None
    parts = numero_control.split("-")
    if not parts:
        return None
    last_segment = parts[-1]
    if not last_segment.isdigit():
        return None
    return int(last_segment)


def _ensure_dte_identifiers(
    invoice: Invoice,
    tipo_dte: str,
    staff_user: StaffUser | None,
) -> tuple[str, str, int | None, dict, str, str]:
    ambiente = "01"
    emitter_info, rubro_code, rubro_name = _resolve_emitter_info(staff_user)
    est_code = emitter_info["codEstable"]
    pv_code = emitter_info["codPuntoVenta"]

    codigo_generacion = (invoice.codigo_generacion or "").strip() or str(uuid.uuid4()).upper()
    numero_control = (invoice.numero_control or "").strip()
    control_number_value = _parse_control_number_value(numero_control)

    if not numero_control:
        now_local = timezone.localtime()
        numero_control, control_number_value = _build_numero_control(
            ambiente,
            tipo_dte,
            now_local.date(),
            est_code,
            pv_code,
        )

    updates = []
    if invoice.codigo_generacion != codigo_generacion:
        invoice.codigo_generacion = codigo_generacion
        updates.append("codigo_generacion")
    if invoice.numero_control != numero_control:
        invoice.numero_control = numero_control
        updates.append("numero_control")
    if invoice.dte_status != "PENDIENTE":
        invoice.dte_status = "PENDIENTE"
        updates.append("dte_status")
    if invoice.estado_dte != "PENDIENTE":
        invoice.estado_dte = "PENDIENTE"
        updates.append("estado_dte")

    if updates:
        invoice.save(update_fields=updates)

    return numero_control, codigo_generacion, control_number_value, emitter_info, rubro_code, rubro_name


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


def _apply_invoice_send_update(
    invoice: Invoice,
    status_value: str,
    user_message: str,
    *,
    error_message: str | None = None,
    error_code: str | None = None,
    mark_api_down: bool = False,
) -> None:
    normalized_status = (status_value or "PENDIENTE").upper()
    invoice.dte_status = normalized_status
    invoice.estado_dte = normalized_status
    if error_message is None:
        invoice.last_dte_error = None
    else:
        invoice.last_dte_error = error_message
    invoice.last_dte_error_code = error_code
    invoice.save(
        update_fields=[
            "dte_status",
            "estado_dte",
            "last_dte_sent_at",
            "dte_send_attempts",
            "last_dte_error",
            "last_dte_error_code",
        ]
    )
    invoice._dte_message = user_message
    if mark_api_down:
        invoice._dte_pending_due_to_api_down = True


def _bump_invoice_send_attempt(invoice: Invoice) -> None:
    invoice.dte_send_attempts = (invoice.dte_send_attempts or 0) + 1
    invoice.last_dte_sent_at = timezone.now()


def _should_treat_as_api_down(response: requests.Response | None) -> bool:
    if response is None:
        return True
    status_code = response.status_code
    return status_code >= 500


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
        estado_h = hresp.get("estado")
        desc = hresp.get("descripcionMsg") or error.get("message")
        if estado_h or desc:
            desc = desc or "El DTE fue rechazado por Hacienda."
            msg = f"Hacienda rechazó el DTE: {desc}"
            return "RECHAZADO", estado_h or "RECHAZADO", msg
        msg = "El puente de Hacienda no registró el DTE; se mantendrá PENDIENTE."
        return "PENDIENTE", "SIN_RESPUESTA", msg

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


def _send_dte_payload(
    *,
    invoice: Invoice,
    dte_type: str,
    payload: dict,
    url: str,
    control_number: str,
    control_number_value: int | None,
    issuer_nit: str,
    receiver_nit: str,
    receiver_name: str,
    issue_date,
    total_amount,
    ambiente: str,
    tipo_dte: str,
    est_code: str,
    pv_code: str,
    staff_user: StaffUser | None,
    rubro_code: str,
    rubro_name: str,
) -> DTERecord:
    print(f'\nENDPOINT DTE: "{url}"\n')
    print("\nJSON DTE ENVIO:\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    record = DTERecord.objects.create(
        invoice=invoice,
        dte_type=dte_type,
        status="ENVIANDO",
        control_number=control_number,
        issuer_nit=issuer_nit,
        receiver_nit=receiver_nit,
        receiver_name=receiver_name,
        issue_date=issue_date,
        total_amount=total_amount,
        request_payload=payload,
    )
    logger.info(
        "Enviando DTE %s con rubro %s (%s) para usuario %s",
        dte_type,
        rubro_code,
        rubro_name,
        staff_user.id if staff_user else "anonimo",
    )
    headers = {
        "Authorization": "Bearer api_key_cliente_12172402231026",
        "Content-Type": "application/json",
    }

    try:
        _bump_invoice_send_attempt(invoice)
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

        _apply_invoice_send_update(
            invoice,
            "PENDIENTE",
            PENDING_DTE_MESSAGE,
            error_message=str(exc),
            error_code="network_error",
            mark_api_down=True,
        )

        return record

    try:
        if _should_treat_as_api_down(response):
            record.response_payload = {
                "success": None,
                "error": {
                    "type": "api_unavailable",
                    "message": response.text,
                    "status_code": response.status_code,
                },
            }
            record.hacienda_state = "SIN_RESPUESTA"
            record.status = "PENDIENTE"
            record.save(update_fields=["response_payload", "hacienda_state", "status"])

            _apply_invoice_send_update(
                invoice,
                "PENDIENTE",
                PENDING_DTE_MESSAGE,
                error_message=response.text,
                error_code=str(response.status_code),
                mark_api_down=True,
            )

            return record
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        estado_interno, estado_hacienda, user_message = interpret_dte_response(response_data)
        record.hacienda_state = estado_hacienda
        record.status = estado_interno
        record.save(update_fields=["response_payload", "hacienda_uuid", "hacienda_state", "status"])

        if estado_hacienda == "PROCESADO" and control_number_value:
            _mark_control_number_processed(
                ambiente,
                tipo_dte,
                issue_date,
                est_code,
                pv_code,
                control_number_value,
            )

        _apply_invoice_send_update(
            invoice,
            estado_interno,
            user_message,
            error_message=None,
            error_code=None,
        )
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending %s DTE", dte_type, exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "PENDIENTE"
        record.hacienda_state = "SIN_RESPUESTA"
        record.save(update_fields=["response_payload", "status", "hacienda_state"])
        _apply_invoice_send_update(
            invoice,
            "PENDIENTE",
            "El DTE se ha dejado en estado PENDIENTE por un error inesperado.",
            error_message=str(exc),
            error_code="unexpected_error",
        )
        return record


DEFAULT_RUBRO_CODE = "64922"

DEFAULT_EMITTER_INFO = {
    "nit": "12172402231026",
    "nrc": "3255304",
    "nombre": "EDWIN ARNULFO MATA CASTILLO",
    "nombreComercial": "RELITE GROUP",
    "codActividad": "64922",
    "descActividad": "Tipos de Creditos N.C.P",
    "direccion": {
        "municipio": "22",
        "complemento": "AV. BARCELONA POLIGONO B, RESIDENCIAL SEVILLA, #21, SAN MIGUEL",
        "departamento": "12",
    },
    "telefono": "77961054",
    "correo": "infodte@relitegroup.com",
    "codEstable": "M001",
    "codPuntoVenta": "P001",
    "codPuntoVentaMH": "P001",
    "codEstableMH": "M001",
    "tipoEstablecimiento": "02",
}


def _resolve_emitter_info(staff_user: StaffUser | None) -> tuple[dict, str, str]:
    rubro_code = DEFAULT_RUBRO_CODE
    if staff_user and staff_user.active_rubro_code:
        rubro_code = staff_user.active_rubro_code

    profile = IssuerProfile.objects.filter(rubro_code=rubro_code, is_active=True).first()
    if not profile:
        profile = IssuerProfile.objects.filter(is_active=True).order_by("rubro_code").first()

    if profile:
        emitter_info = {**profile.emisor_schema}
        emitter_info["codActividad"] = profile.rubro_code
        emitter_info["descActividad"] = profile.rubro_name
        rubro_code = profile.rubro_code
        rubro_name = profile.rubro_name
    else:
        emitter_info = {**DEFAULT_EMITTER_INFO}
        rubro_code = emitter_info.get("codActividad", DEFAULT_RUBRO_CODE)
        rubro_name = emitter_info.get(
            "descActividad",
            "Actividades Inmobiliarias Realizadas a Cambio de una Retribucion o por Contrata",
        )

    if staff_user and staff_user.active_rubro_code != rubro_code:
        staff_user.active_rubro_code = rubro_code
        staff_user.save(update_fields=["active_rubro_code"])

    return emitter_info, rubro_code, rubro_name


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_currency(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _build_receptor(invoice, emitter_info: dict):
    client = getattr(invoice, "client", None)
    emitter_address = emitter_info["direccion"]
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


def send_cf_dte_for_invoice(invoice, staff_user: StaffUser | None = None) -> DTERecord:
    """
    Construye el JSON DTE para tipo CF a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    ambiente = "01"
    (
        numero_control,
        codigo_generacion,
        control_number_value,
        emitter_info,
        rubro_code,
        rubro_name,
    ) = _ensure_dte_identifiers(invoice, "01", staff_user)
    est_code = emitter_info["codEstable"]
    pv_code = emitter_info["codPuntoVenta"]

    now_local = timezone.localtime()
    emision_date = now_local.date()
    fec_emi = emision_date.isoformat()
    hor_emi = now_local.strftime("%H:%M:%S")

    receptor, receiver_nit, receiver_name = _build_receptor(invoice, emitter_info)
    receiver_doc_for_extension = _resolve_receiver_doc_for_extension(
        getattr(invoice, "client", None),
        f"CF invoice {invoice.id}",
    )
    items: list[InvoiceItem] = list(invoice.items.select_related("service"))

    cuerpo_documento = []
    total_base = Decimal("0.00")
    total_iva = Decimal("0.00")
    total_gross = Decimal("0.00")
    total_no_suj = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        unit_price = Decimal(str(item.unit_price))
        quantity = Decimal(str(item.quantity))
        gross_line = quantity * unit_price

        is_no_sujeta = bool(getattr(item, "is_no_sujeta", False))
        if is_no_sujeta:
            base_line = Decimal("0.00")
            iva_line = Decimal("0.00")
            total_no_suj += gross_line
        else:
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
                "ventaGravada": 0 if is_no_sujeta else float(_round_2(gross_line)),
                "codTributo": None,
                "numItem": index,
                "psv": 0,
                "ventaNoSuj": float(_round_2(gross_line)) if is_no_sujeta else 0,
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
    total_no_suj = _round_2(total_no_suj)
    monto_total_operacion = _round_2(total_gross + total_no_suj)
    total_pagar = monto_total_operacion

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
        "subTotal": float(monto_total_operacion),
        "totalLetras": amount_to_spanish_words(monto_total_operacion),
        "descuNoSuj": 0,
        "subTotalVentas": float(monto_total_operacion),
        "reteRenta": 0,
        "tributos": None,
        "totalNoSuj": float(total_no_suj),
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
                **emitter_info,
            },
            "documentoRelacionado": None,
            "ventaTercero": None,
            "otrosDocumentos": None,
            "receptor": receptor,
        }
    }

    url = "https://p12172402231026.cheros.dev/api/v1/dte/factura"
    return _send_dte_payload(
        invoice=invoice,
        dte_type="CF",
        payload=payload,
        url=url,
        control_number=numero_control,
        control_number_value=control_number_value,
        issuer_nit=emitter_info["nit"],
        receiver_nit=receiver_nit,
        receiver_name=receiver_name,
        issue_date=emision_date,
        total_amount=invoice.total,
        ambiente=ambiente,
        tipo_dte="01",
        est_code=est_code,
        pv_code=pv_code,
        staff_user=staff_user,
        rubro_code=rubro_code,
        rubro_name=rubro_name,
    )


def send_ccf_dte_for_invoice(invoice, staff_user: StaffUser | None = None) -> DTERecord:
    """
    Construye el JSON DTE para tipo CCF (03) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    ambiente = "01"
    (
        numero_control,
        codigo_generacion,
        control_number_value,
        emitter_info,
        rubro_code,
        rubro_name,
    ) = _ensure_dte_identifiers(invoice, "03", staff_user)
    est_code = emitter_info["codEstable"]
    pv_code = emitter_info["codPuntoVenta"]

    now_local = timezone.localtime()
    emision_date = now_local.date()
    fec_emi = emision_date.isoformat()
    hor_emi = now_local.strftime("%H:%M:%S")

    client = getattr(invoice, "client", None)
    emitter_address = emitter_info["direccion"]

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
    total_no_suj = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        gross_unit = Decimal(str(item.unit_price))
        qty_dec = Decimal(str(item.quantity))
        gross_line = gross_unit * qty_dec
        is_no_sujeta = bool(getattr(item, "is_no_sujeta", False))
        if is_no_sujeta:
            line_base = gross_line
            iva_line = Decimal("0.00")
            total_no_suj += gross_line
        else:
            line_base, iva_line = split_gross_amount_with_tax(gross_line)
            total_base += line_base
            total_iva += iva_line
        total_gross += gross_line

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
                "tributos": None if is_no_sujeta else ["20"],
                "uniMedida": 59,
                "noGravado": 0,
                "codTributo": None,
                "montoDescu": 0,
                "ventaNoSuj": float(_round_2(gross_line)) if is_no_sujeta else 0,
                "psv": 0,
                "precioUni": float(precio_base_unitario),
                "descripcion": descripcion,
                "ventaGravada": 0 if is_no_sujeta else float(_round_2(line_base)),
                "numeroDocumento": None,
            }
        )

    total_gross = _round_2(total_gross)
    total_base = _round_2(total_base)
    total_iva = _round_2(total_iva)
    total_no_suj = _round_2(total_no_suj)
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
        "subTotal": float(total_base + total_no_suj),
        "totalLetras": total_letras,
        "descuNoSuj": 0,
        "subTotalVentas": float(total_base + total_no_suj),
        "reteRenta": 0,
        "tributos": (
            [
                {
                    "valor": float(total_iva),
                    "descripcion": "Impuesto al Valor Agregado 13%",
                    "codigo": "20",
                }
            ]
            if total_iva > 0
            else None
        ),
        "totalNoSuj": float(total_no_suj),
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
            "emisor": {**emitter_info},
            "documentoRelacionado": None,
            "ventaTercero": None,
            "otrosDocumentos": None,
            "receptor": receptor,
        }
    }

    url = "https://p12172402231026.cheros.dev/api/v1/dte/credito-fiscal"
    return _send_dte_payload(
        invoice=invoice,
        dte_type="CCF",
        payload=payload,
        url=url,
        control_number=numero_control,
        control_number_value=control_number_value,
        issuer_nit=emitter_info["nit"],
        receiver_nit=client_nit,
        receiver_name=client_name,
        issue_date=emision_date,
        total_amount=_to_decimal(total_operacion),
        ambiente=ambiente,
        tipo_dte="03",
        est_code=est_code,
        pv_code=pv_code,
        staff_user=staff_user,
        rubro_code=rubro_code,
        rubro_name=rubro_name,
    )


def send_se_dte_for_invoice(invoice, staff_user: StaffUser | None = None) -> DTERecord:
    """
    Construye el JSON DTE para tipo Sujeto Excluido (14) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    ambiente = "01"
    (
        numero_control,
        codigo_generacion,
        control_number_value,
        emitter_info,
        rubro_code,
        rubro_name,
    ) = _ensure_dte_identifiers(invoice, "14", staff_user)
    est_code = emitter_info["codEstable"]
    pv_code = emitter_info["codPuntoVenta"]

    now_local = timezone.localtime()
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
        or emitter_info["direccion"].get("departamento", "12")
    )
    se_municipio = (
        getattr(client, "municipality_code", None)
        or emitter_info["direccion"].get("municipio", "22")
    )
    se_direccion = getattr(client, "address", None) or emitter_info["direccion"].get(
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
                "correo": emitter_info["correo"],
                "codPuntoVenta": emitter_info["codPuntoVenta"],
                "nombre": emitter_info["nombre"],
                "codEstableMH": emitter_info["codEstableMH"],
                "direccion": emitter_info["direccion"],
                "codPuntoVentaMH": emitter_info["codPuntoVentaMH"],
                "codEstable": emitter_info["codEstable"],
                "nit": emitter_info["nit"],
                "nrc": emitter_info["nrc"],
                "telefono": emitter_info["telefono"],
                "codActividad": emitter_info["codActividad"],
                "descActividad": emitter_info["descActividad"],
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

    url = "https://p12172402231026.cheros.dev/api/v1/dte/sujeto-excluido"
    return _send_dte_payload(
        invoice=invoice,
        dte_type="SE",
        payload=payload,
        url=url,
        control_number=numero_control,
        control_number_value=control_number_value,
        issuer_nit=emitter_info["nit"],
        receiver_nit=se_num_documento,
        receiver_name=se_nombre,
        issue_date=emision_date,
        total_amount=_to_decimal(total_pagar),
        ambiente=ambiente,
        tipo_dte="14",
        est_code=est_code,
        pv_code=pv_code,
        staff_user=staff_user,
        rubro_code=rubro_code,
        rubro_name=rubro_name,
    )


def send_dte_for_invoice(invoice, staff_user: StaffUser | None = None) -> DTERecord | None:
    if invoice.doc_type == Invoice.CF:
        return send_cf_dte_for_invoice(invoice, staff_user=staff_user)
    if invoice.doc_type == Invoice.CCF:
        return send_ccf_dte_for_invoice(invoice, staff_user=staff_user)
    if invoice.doc_type == Invoice.SX:
        return send_se_dte_for_invoice(invoice, staff_user=staff_user)
    return None


def resend_pending_dtes(limit: int = 50) -> int:
    resent = 0
    with transaction.atomic():
        pending_invoices = list(
            Invoice.objects.select_for_update(skip_locked=True)
            .filter(
                models.Q(dte_status__iexact="pendiente")
                | models.Q(estado_dte__iexact="pendiente"),
            )
            .order_by("id")[:limit]
        )

        for invoice in pending_invoices:
            status_label = (invoice.dte_status or invoice.estado_dte or "").upper()
            if status_label in {"ACEPTADO", "RECHAZADO"}:
                continue
            send_dte_for_invoice(invoice, staff_user=None)
            resent += 1
    return resent
