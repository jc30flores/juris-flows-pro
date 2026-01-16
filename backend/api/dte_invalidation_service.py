import json
import logging
import time
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .dte_auth import build_dte_headers, mask_headers
from .dte_config import get_mh_ambiente
from .dte_cf_service import EMITTER_INFO
from .dte_urls import build_dte_url
from .models import DTEInvalidation, DTERecord, Invoice, StaffUser

logger = logging.getLogger(__name__)

INVALIDATION_AUTH_TOKEN = "api_key_cliente_12152606851014"
INVALIDATION_PATH = "/api/v1/dte/invalidacion"
DEFAULT_INVALIDATION_CONNECT_TIMEOUT = int(
    getattr(settings, "DTE_INVALIDATION_CONNECT_TIMEOUT", 5)
)
DEFAULT_INVALIDATION_READ_TIMEOUT = int(
    getattr(settings, "DTE_INVALIDATION_READ_TIMEOUT", 25)
)
DEFAULT_INVALIDATION_TIMEOUT = (
    DEFAULT_INVALIDATION_CONNECT_TIMEOUT,
    DEFAULT_INVALIDATION_READ_TIMEOUT,
)
DEFAULT_VERIFY_SSL = bool(getattr(settings, "DTE_INVALIDATION_VERIFY_SSL", True))


def _coerce_payload(payload) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("DTE payload corrupto/no parseable.") from exc
        if isinstance(parsed, dict):
            return parsed
        return {}
    return {}


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


def _truncate_text(value: str, limit: int = 8000) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...[truncated]"


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
    request_payload = _coerce_payload(record.request_payload)
    response_payload = _coerce_payload(record.response_payload)
    ident = _extract_identification(request_payload)
    resumen = _extract_resumen(request_payload)
    receptor = _extract_receptor(request_payload)

    ambiente = ident.get("ambiente") or get_mh_ambiente()
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
    request_payload = _coerce_payload(record.request_payload)
    response_payload = _coerce_payload(record.response_payload)
    ident = _extract_identification(request_payload)
    fec_emi = ident.get("fecEmi") or ident.get("fec_emi")
    if not fec_emi and record.issue_date:
        fec_emi = record.issue_date.isoformat()
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
        "sello_recibido": _extract_sello_recibido(response_payload) or "",
        "fec_emi": fec_emi or "",
        "ambiente": ident.get("ambiente") or get_mh_ambiente(),
    }


def send_dte_invalidation(
    invoice: Invoice,
    *,
    tipo_anulacion: int = 2,
    motivo_anulacion: str = "",
    staff_user_id: int | None = None,
) -> tuple[DTEInvalidation, dict | str, int, str, str, str | None]:
    record = invoice.dte_records.order_by("-created_at").first()
    if not record:
        raise ValueError("No se encontró un DTERecord asociado a la factura.")

    raw_invalidation_url = str(
        getattr(settings, "DTE_API_INVALIDACION_URL", "") or ""
    ).strip()
    invalidation_url = raw_invalidation_url or build_dte_url(INVALIDATION_PATH)
    if invalidation_url and INVALIDATION_PATH not in invalidation_url:
        logger.warning(
            "Invalidation URL missing path; normalizing. original=%s",
            invalidation_url,
        )
        invalidation_url = f"{invalidation_url.rstrip('/')}{INVALIDATION_PATH}"
    if invalidation_url:
        print("[DTE INVALIDACION] URL:", invalidation_url)

    payload = build_invalidation_payload(
        invoice,
        record,
        tipo_anulacion=tipo_anulacion,
        motivo_anulacion=motivo_anulacion,
        staff_user=_resolve_staff_user(staff_user_id),
    )

    invalidation = DTEInvalidation.objects.create(
        invoice=invoice,
        status="ENVIANDO",
        hacienda_state="",
        request_payload=payload,
        response_payload=None,
    )

    if not invalidation_url:
        detail = "DTE_BASE_URL no configurada."
        invalidation.response_payload = {
            "success": None,
            "error": {"type": "config", "message": detail},
        }
        invalidation.hacienda_state = "ERROR_CONFIG"
        invalidation.status = "ERROR_CONFIG"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        return invalidation, invalidation.response_payload, 503, "CONFIG_FALTANTE", detail, None

    headers = build_dte_headers()
    logger.info(
        "Sending DTE invalidation invoice_id=%s url=%s dte_status=%s timeout=%s verify_ssl=%s headers=%s payload=%s",
        invoice.id,
        invalidation_url,
        invoice.dte_status,
        DEFAULT_INVALIDATION_TIMEOUT,
        DEFAULT_VERIFY_SSL,
        mask_headers(headers),
        json.dumps(payload, indent=2, ensure_ascii=False),
    )
    print(
        "[DTE INVALIDACION] Payload:\n",
        json.dumps(payload, indent=2, ensure_ascii=False),
    )

    print("[DTE INVALIDACION] Headers:", mask_headers(headers))

    started_at = time.monotonic()
    try:
        response = requests.post(
            invalidation_url,
            json=payload,
            headers=headers,
            timeout=DEFAULT_INVALIDATION_TIMEOUT,
            verify=DEFAULT_VERIFY_SSL,
        )
    except requests.exceptions.RequestException as exc:
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.warning(
            "DTE invalidation request failed invoice_id=%s elapsed_ms=%s error=%s",
            invoice.id,
            elapsed_ms,
            exc,
        )
        logger.exception(
            "DTE invalidation request exception invoice_id=%s", invoice.id
        )
        invalidation.response_payload = {
            "success": None,
            "error": {"type": "network_error", "message": str(exc)},
        }
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        detail = "Sin conexión al puente; se reintentará."
        return invalidation, invalidation.response_payload, 202, "PENDIENTE", detail, None

    try:
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        invalidation.response_payload = response_data
        status_code = response.status_code
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        response_text = ""
        try:
            response_text = response.text or ""
        except Exception:  # pragma: no cover - defensive
            response_text = ""
        logger.info(
            "DTE invalidation response invoice_id=%s status_code=%s elapsed_ms=%s headers=%s body=%s",
            invoice.id,
            status_code,
            elapsed_ms,
            dict(response.headers),
            _truncate_text(response_text),
        )
        print("[DTE INVALIDACION] Bridge status:", status_code)
        print(
            "[DTE INVALIDACION] Bridge body:\n",
            _truncate_text(response_text),
        )
        if isinstance(response_data, dict):
            logger.info(
                "DTE invalidation response json invoice_id=%s payload=%s",
                invoice.id,
                json.dumps(response_data, indent=2, ensure_ascii=False),
            )
            print(
                "[DTE INVALIDACION] Bridge JSON:\n",
                json.dumps(response_data, indent=2, ensure_ascii=False),
            )

        if status_code in (401, 403):
            bridge_error = (
                response_data
                if isinstance(response_data, dict)
                else {"raw_text": _truncate_text(response_text)}
            )
            bridge_error = {
                "bridge_url": invalidation_url,
                "bridge_status": status_code,
                "bridge_body": bridge_error,
            }
            invalidation.hacienda_state = "NO_AUTENTICADO"
            invalidation.status = "NO_AUTENTICADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            detail = "No autenticado contra el puente DTE"
            return invalidation, response_data, status_code, "NO_AUTENTICADO", detail, bridge_error

        if status_code >= 500:
            bridge_error = (
                response_data
                if isinstance(response_data, dict)
                else {"raw_text": _truncate_text(response_text)}
            )
            bridge_error = {
                "bridge_url": invalidation_url,
                "bridge_status": status_code,
                "bridge_body": bridge_error,
            }
            invalidation.hacienda_state = "ERROR_PUENTE"
            invalidation.status = "ERROR_PUENTE"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            detail = "Puente devolvió error"
            return invalidation, response_data, 502, "ERROR_PUENTE", detail, bridge_error

        if status_code >= 400:
            bridge_error = (
                response_data
                if isinstance(response_data, dict)
                else {"raw_text": _truncate_text(response_text)}
            )
            bridge_error = {
                "bridge_url": invalidation_url,
                "bridge_status": status_code,
                "bridge_body": bridge_error,
            }
            invalidation.hacienda_state = "RECHAZADO"
            invalidation.status = "RECHAZADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            detail = "Puente rechazó la invalidación"
            return invalidation, response_data, 422, "RECHAZADO", detail, bridge_error

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
            detail = "La invalidación fue aceptada por Hacienda."
            return invalidation, response_data, 200, "ACEPTADO", detail, None

        if success is False:
            invalidation.hacienda_state = estado_hacienda or "RECHAZADO"
            invalidation.status = "RECHAZADO"
            invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
            detail = "La invalidación fue rechazada por Hacienda."
            return invalidation, response_data, 422, "RECHAZADO", detail, None

        invalidation.hacienda_state = estado_hacienda or "DESCONOCIDO"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        detail = "La invalidación quedó en estado pendiente."
        return invalidation, response_data, 200, "PENDIENTE", detail, None
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending DTE invalidation", exc_info=exc)
        invalidation.response_payload = {"error": str(exc)}
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.status = "PENDIENTE"
        invalidation.save(update_fields=["response_payload", "hacienda_state", "status"])
        detail = "Error interno al procesar la invalidación."
        return invalidation, invalidation.response_payload, 500, "PENDIENTE", detail, None
