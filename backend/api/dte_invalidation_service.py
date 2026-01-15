import json
import logging
import uuid
from decimal import Decimal

import requests
from django.utils import timezone

from .dte_cf_service import EMITTER_INFO
from .models import DTEInvalidation, DTERecord, Invoice, StaffUser

logger = logging.getLogger(__name__)

INVALIDATION_URL = "https://t12152606851014.cheros.dev/api/v1/dte/invalidacion"
INVALIDATION_AUTH_TOKEN = "api_key_cliente_12152606851014"


def _extract_payload_container(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    dte_payload = payload.get("dte")
    if isinstance(dte_payload, dict):
        return dte_payload
    documento = payload.get("documento")
    if isinstance(documento, dict):
        return documento
    return payload


def _extract_identification(payload: dict) -> dict:
    container = _extract_payload_container(payload)
    ident = container.get("identificacion")
    if isinstance(ident, dict):
        return ident
    return {}


def _extract_resumen(payload: dict) -> dict:
    container = _extract_payload_container(payload)
    resumen = container.get("resumen")
    if isinstance(resumen, dict):
        return resumen
    return {}


def _extract_receptor(payload: dict) -> dict:
    container = _extract_payload_container(payload)
    receptor = container.get("receptor")
    if isinstance(receptor, dict):
        return receptor
    return {}


def _extract_sello_recibido(payload: dict) -> str | None:
    if not isinstance(payload, dict):
        return None
    hresp = payload.get("respuesta_hacienda") or payload.get("hacienda_response")
    if not isinstance(hresp, dict):
        hresp = payload.get("respuestaHacienda") or payload.get("haciendaResponse")
    if not isinstance(hresp, dict):
        return None
    return hresp.get("selloRecibido") or hresp.get("sello_recibido")


def _normalize_phone(value: str | None) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) >= 8:
        return digits[-8:]
    if not digits:
        return "00000000"
    return digits.rjust(8, "0")


def _coerce_decimal(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal("0")


def _resolve_staff_user(staff_user_id: int | None) -> StaffUser | None:
    if not staff_user_id:
        return None
    return StaffUser.objects.filter(id=staff_user_id).first()


def _resolve_staff_name(staff_user: StaffUser | None) -> str:
    if staff_user:
        return staff_user.full_name or staff_user.username or EMITTER_INFO["nombre"]
    return EMITTER_INFO["nombre"]


def _resolve_receiver_doc(receptor: dict, invoice: Invoice) -> str:
    for key in ("numDocumento", "numeroDocumento", "num_documento"):
        value = receptor.get(key)
        if value:
            return str(value)
    client = getattr(invoice, "client", None)
    if client:
        return client.nit or client.dui or "00000000-0"
    return "00000000-0"


def _resolve_receiver_name(receptor: dict, invoice: Invoice) -> str:
    nombre = receptor.get("nombre")
    if nombre:
        return str(nombre)
    client = getattr(invoice, "client", None)
    if client:
        return client.company_name or client.full_name or "CONSUMIDOR FINAL"
    return "CONSUMIDOR FINAL"


def _resolve_receiver_phone(receptor: dict, invoice: Invoice) -> str:
    telefono = receptor.get("telefono")
    if telefono:
        return _normalize_phone(telefono)
    client = getattr(invoice, "client", None)
    return _normalize_phone(getattr(client, "phone", "")) if client else "00000000"


def _resolve_receiver_email(receptor: dict, invoice: Invoice) -> str:
    correo = receptor.get("correo")
    if correo:
        return str(correo)
    client = getattr(invoice, "client", None)
    if client and client.email:
        return client.email
    return ""


def _build_emisor_payload() -> dict:
    nom_establecimiento = (
        EMITTER_INFO.get("nomEstablecimiento")
        or EMITTER_INFO.get("nombreComercial")
        or EMITTER_INFO.get("nombre")
        or ""
    )
    return {
        "nit": EMITTER_INFO.get("nit", ""),
        "nombre": EMITTER_INFO.get("nombre", ""),
        "tipoEstablecimiento": EMITTER_INFO.get("tipoEstablecimiento", ""),
        "nomEstablecimiento": nom_establecimiento,
        "codEstableMH": EMITTER_INFO.get("codEstableMH", ""),
        "codEstable": EMITTER_INFO.get("codEstable", ""),
        "codPuntoVentaMH": EMITTER_INFO.get("codPuntoVentaMH", ""),
        "codPuntoVenta": EMITTER_INFO.get("codPuntoVenta", ""),
        "telefono": _normalize_phone(EMITTER_INFO.get("telefono", "")),
        "correo": EMITTER_INFO.get("correo", ""),
    }


def _build_motivo_payload(
    *,
    tipo_anulacion: int,
    motivo_anulacion: str,
    staff_user: StaffUser | None,
) -> dict:
    default_motivo = "Rescindir de la operación realizada"
    responsible_name = _resolve_staff_name(staff_user)
    emisor_nit = EMITTER_INFO.get("nit", "")
    return {
        "tipoAnulacion": int(tipo_anulacion) if tipo_anulacion else 2,
        "motivoAnulacion": motivo_anulacion or default_motivo,
        "nombreResponsable": responsible_name or "",
        "tipDocResponsable": "36",
        "numDocResponsable": emisor_nit or "",
        "nombreSolicita": responsible_name or "",
        "tipDocSolicita": "36",
        "numDocSolicita": emisor_nit or "",
    }


def build_invalidation_payload(
    invoice: Invoice,
    record: DTERecord,
    *,
    tipo_anulacion: int = 2,
    motivo_anulacion: str = "",
    staff_user: StaffUser | None = None,
) -> dict:
    request_payload = record.request_payload or {}
    response_payload = record.response_payload or {}
    ident = _extract_identification(request_payload)
    resumen = _extract_resumen(request_payload)
    receptor = _extract_receptor(request_payload)

    ambiente = ident.get("ambiente") or "01"
    codigo_generacion = (
        ident.get("codigoGeneracion")
        or ident.get("codigo_generacion")
        or record.hacienda_uuid
        or ""
    )
    numero_control = (
        ident.get("numeroControl")
        or ident.get("numero_control")
        or record.control_number
        or ""
    )
    fec_emi = ident.get("fecEmi") or ident.get("fec_emi")
    if not fec_emi and record.issue_date:
        fec_emi = record.issue_date.isoformat()

    sello_recibido = _extract_sello_recibido(response_payload)
    now_local = timezone.localtime()

    documento_payload = {
        "tipoDte": ident.get("tipoDte") or "",
        "codigoGeneracion": codigo_generacion,
        "numeroControl": numero_control,
        "selloRecibido": sello_recibido or "",
        "fecEmi": fec_emi or "",
        "montoIva": float(_coerce_decimal(resumen.get("totalIva", 0))),
        "codigoGeneracionR": None,
        "tipoDocumento": receptor.get("tipoDocumento") or "13",
        "numDocumento": _resolve_receiver_doc(receptor, invoice),
        "nombre": _resolve_receiver_name(receptor, invoice),
        "telefono": _resolve_receiver_phone(receptor, invoice),
        "correo": _resolve_receiver_email(receptor, invoice),
    }

    payload = {
        "invalidacion": {
            "identificacion": {
                "version": 2,
                "ambiente": ambiente,
                "codigoGeneracion": str(uuid.uuid4()).upper(),
                "fecAnula": now_local.date().isoformat(),
                "horAnula": now_local.strftime("%H:%M:%S"),
            },
            "emisor": _build_emisor_payload(),
            "documento": documento_payload,
            "motivo": _build_motivo_payload(
                tipo_anulacion=tipo_anulacion,
                motivo_anulacion=motivo_anulacion,
                staff_user=staff_user,
            ),
        }
    }
    return payload


def extract_invalidation_requirements(record: DTERecord) -> dict:
    request_payload = record.request_payload or {}
    ident = _extract_identification(request_payload)
    return {
        "codigo_generacion": (
            ident.get("codigoGeneracion")
            or ident.get("codigo_generacion")
            or record.hacienda_uuid
            or ""
        ),
        "numero_control": (
            ident.get("numeroControl")
            or ident.get("numero_control")
            or record.control_number
            or ""
        ),
        "sello_recibido": _extract_sello_recibido(record.response_payload or {}) or "",
        "fec_emi": ident.get("fecEmi") or ident.get("fec_emi") or "",
        "ambiente": ident.get("ambiente") or "01",
    }


def send_dte_invalidation(
    invoice: Invoice,
    *,
    tipo_anulacion: int = 2,
    motivo_anulacion: str = "",
    staff_user_id: int | None = None,
) -> tuple[DTEInvalidation, dict | str, int, str]:
    record = invoice.dte_records.order_by("-created_at").first()
    if not record:
        raise ValueError("No se encontró un DTERecord asociado a la factura.")

    payload = build_invalidation_payload(
        invoice,
        record,
        tipo_anulacion=tipo_anulacion,
        motivo_anulacion=motivo_anulacion,
        staff_user=_resolve_staff_user(staff_user_id),
    )

    logger.info(
        "Sending DTE invalidation invoice_id=%s url=%s headers=Bearer *** payload=%s",
        invoice.id,
        INVALIDATION_URL,
        json.dumps(payload, indent=2, ensure_ascii=False),
    )

    invalidation = DTEInvalidation.objects.create(
        invoice=invoice,
        status="ENVIANDO",
        hacienda_state="",
        request_payload=payload,
        response_payload=None,
    )

    headers = {
        "Authorization": f"Bearer {INVALIDATION_AUTH_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            INVALIDATION_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        invalidation.response_payload = {
            "success": None,
            "error": {"type": "network_error", "message": str(exc)},
        }
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        return invalidation, invalidation.response_payload, 202, "PENDIENTE"

    try:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        invalidation.response_payload = response_data
        status_code = response.status_code

        if status_code >= 500:
            invalidation.hacienda_state = "ERROR_PUENTE"
            invalidation.status = "ERROR_PUENTE"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            return invalidation, response_data, 502, "ERROR_PUENTE"

        if status_code >= 400:
            invalidation.hacienda_state = "RECHAZADO"
            invalidation.status = "RECHAZADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            return invalidation, response_data, 422, "RECHAZADO"

        success = response_data.get("success") if isinstance(response_data, dict) else None
        hresp = (
            response_data.get("respuesta_hacienda")
            or response_data.get("hacienda_response")
            if isinstance(response_data, dict)
            else {}
        )
        if not isinstance(hresp, dict):
            hresp = {}
        estado_hacienda = hresp.get("estado", "") if isinstance(hresp, dict) else ""

        if success is True and estado_hacienda in ("PROCESADO", "RECIBIDO"):
            invalidation.hacienda_state = estado_hacienda or "RECIBIDO"
            invalidation.status = "ACEPTADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            invoice.dte_status = Invoice.INVALIDATED
            invoice.save(update_fields=["dte_status"])
            return invalidation, response_data, 200, "ACEPTADO"

        if success is False:
            invalidation.hacienda_state = estado_hacienda or "RECHAZADO"
            invalidation.status = "RECHAZADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            return invalidation, response_data, 422, "RECHAZADO"

        invalidation.hacienda_state = estado_hacienda or "DESCONOCIDO"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        return invalidation, response_data, 200, "PENDIENTE"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending DTE invalidation", exc_info=exc)
        invalidation.response_payload = {"error": str(exc)}
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        return invalidation, invalidation.response_payload, 500, "PENDIENTE"
