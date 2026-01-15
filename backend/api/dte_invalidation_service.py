import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .dte_cf_service import interpret_dte_response, _resolve_emitter_info
from .models import DTEInvalidation, DTERecord, Invoice, StaffUser


DEFAULT_INVALIDATION_URL = getattr(
    settings,
    "DTE_INVALIDATION_URL",
    "https://p12172402231026.cheros.dev/api/v1/dte/invalidacion",
)


def _extract_ident(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    if "identificacion" in payload:
        return payload.get("identificacion") or {}
    dte_payload = payload.get("dte")
    if isinstance(dte_payload, dict) and "identificacion" in dte_payload:
        return dte_payload.get("identificacion") or {}
    documento = payload.get("documento")
    if isinstance(documento, dict) and "identificacion" in documento:
        return documento.get("identificacion") or {}
    return {}


def _extract_resumen(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    if "resumen" in payload:
        return payload.get("resumen") or {}
    dte_payload = payload.get("dte")
    if isinstance(dte_payload, dict) and "resumen" in dte_payload:
        return dte_payload.get("resumen") or {}
    documento = payload.get("documento")
    if isinstance(documento, dict) and "resumen" in documento:
        return documento.get("resumen") or {}
    return {}


def _extract_hacienda_response(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    if "respuesta_hacienda" in payload:
        return payload.get("respuesta_hacienda") or {}
    if "hacienda_response" in payload:
        return payload.get("hacienda_response") or {}
    error = payload.get("error")
    if isinstance(error, dict):
        return error.get("respuesta_hacienda") or error.get("hacienda_response") or {}
    return {}


def _get_sello_recibido(payload: dict | None) -> str:
    hresp = _extract_hacienda_response(payload)
    return (
        hresp.get("selloRecibido")
        or hresp.get("sello_recibido")
        or ""
    )


def _resolve_tipo_dte(invoice: Invoice, ident: dict) -> str:
    tipo = ident.get("tipoDte") or ident.get("tipo_dte")
    if tipo:
        return str(tipo)
    mapping = {
        Invoice.CF: "01",
        Invoice.CCF: "03",
        Invoice.SX: "14",
    }
    return mapping.get(invoice.doc_type, "")


def _format_date(value) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def get_invalidation_preview(invoice: Invoice) -> dict:
    record = invoice.dte_records.order_by("-created_at").first()
    if not record:
        raise ValueError("La factura no tiene un DTE registrado para invalidar.")
    ident = _extract_ident(record.request_payload or {})
    sello_recibido = _get_sello_recibido(record.response_payload or {})
    numero_control = (
        (invoice.numero_control or "").strip()
        or (record.control_number or "").strip()
        or (ident.get("numeroControl") or ident.get("numero_control") or "")
    )
    codigo_generacion = (
        (invoice.codigo_generacion or "").strip()
        or (record.hacienda_uuid or "").strip()
        or (ident.get("codigoGeneracion") or ident.get("codigo_generacion") or "")
    )
    tipo_dte = _resolve_tipo_dte(invoice, ident)
    cliente = ""
    client = getattr(invoice, "client", None)
    if client:
        cliente = client.company_name or client.full_name or ""
    return {
        "numero_control": numero_control or None,
        "codigo_generacion": codigo_generacion or None,
        "cliente": cliente or None,
        "fecha_emision": _format_date(invoice.date) or None,
        "tipo_dte": tipo_dte or None,
        "sello_recibido": sello_recibido or None,
    }


def invalidate_dte_for_invoice(
    invoice: Invoice,
    *,
    staff_user: StaffUser | None,
    tipo_anulacion: int,
    motivo_anulacion: str = "",
    url: str | None = None,
) -> tuple[DTEInvalidation, str]:
    record: DTERecord | None = invoice.dte_records.order_by("-created_at").first()
    if not record:
        raise ValueError("La factura no tiene un DTE registrado para invalidar.")

    sello_recibido = _get_sello_recibido(record.response_payload or {})
    if not sello_recibido:
        raise ValueError("No se encontró sello recibido para invalidar este DTE.")

    ident = _extract_ident(record.request_payload or {})
    resumen = _extract_resumen(record.request_payload or {})
    codigo_original = (
        ident.get("codigoGeneracion")
        or ident.get("codigo_generacion")
        or invoice.codigo_generacion
        or record.hacienda_uuid
        or ""
    )
    numero_control = (
        ident.get("numeroControl")
        or ident.get("numero_control")
        or invoice.numero_control
        or record.control_number
        or ""
    )
    tipo_dte = _resolve_tipo_dte(invoice, ident)
    fec_emi = ident.get("fecEmi") or ident.get("fec_emi") or _format_date(invoice.date)
    monto_iva_raw = resumen.get("totalIva") or resumen.get("total_iva")
    monto_iva = Decimal(str(monto_iva_raw)) if monto_iva_raw not in (None, "") else None

    now_local = timezone.localtime()
    codigo_generacion = str(uuid.uuid4()).upper()
    ambiente = ident.get("ambiente") or "01"

    emitter_info, _, _ = _resolve_emitter_info(staff_user)
    responsable_nombre = (
        staff_user.full_name
        if staff_user and staff_user.full_name
        else staff_user.username
        if staff_user and staff_user.username
        else emitter_info.get("nombre", "")
    )
    responsable_doc = emitter_info.get("nit", "")
    motivo_payload = {
        "tipoAnulacion": int(tipo_anulacion),
        "motivoAnulacion": motivo_anulacion or "",
        "nombreResponsable": responsable_nombre,
        "tipDocResponsable": "36" if responsable_doc else "",
        "numDocResponsable": responsable_doc or "",
        "nombreSolicitante": responsable_nombre,
        "tipDocSolicitante": "36" if responsable_doc else "",
        "numDocSolicitante": responsable_doc or "",
    }

    payload = {
        "invalidacion": {
            "identificacion": {
                "version": 1,
                "ambiente": ambiente,
                "codigoGeneracion": codigo_generacion,
                "fecAnula": now_local.strftime("%Y-%m-%d"),
                "horAnula": now_local.strftime("%H:%M:%S"),
            },
            "emisor": {
                **emitter_info,
            },
            "documento": {
                "tipoDte": tipo_dte,
                "codigoGeneracion": codigo_original,
                "numeroControl": numero_control,
                "selloRecibido": sello_recibido,
                "fecEmi": fec_emi,
                "montoIva": float(monto_iva) if monto_iva is not None else None,
            },
            "motivo": motivo_payload,
        }
    }

    invalidation = DTEInvalidation.objects.create(
        invoice=invoice,
        dte_record=record,
        requested_by=staff_user,
        status=DTEInvalidation.SENDING,
        codigo_generacion=codigo_generacion,
        tipo_anulacion=int(tipo_anulacion),
        motivo_anulacion=motivo_anulacion or "",
        original_codigo_generacion=codigo_original or "",
        original_numero_control=numero_control or "",
        original_sello_recibido=sello_recibido or "",
        original_tipo_dte=tipo_dte or "",
        original_fec_emi=fec_emi or "",
        original_monto_iva=monto_iva,
        request_payload=payload,
        sent_at=timezone.now(),
    )

    headers = {
        "Authorization": "Bearer api_key_cliente_12172402231026",
        "Content-Type": "application/json",
    }
    target_url = url or DEFAULT_INVALIDATION_URL

    try:
        response = requests.post(target_url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        invalidation.response_payload = {
            "success": None,
            "error": {
                "type": "network_error",
                "message": str(exc),
            },
        }
        invalidation.status = DTEInvalidation.PENDING
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.error_message = str(exc)
        invalidation.error_code = "network_error"
        invalidation.processed_at = timezone.now()
        invalidation.save(
            update_fields=[
                "response_payload",
                "status",
                "hacienda_state",
                "error_message",
                "error_code",
                "processed_at",
            ]
        )
        return invalidation, "Hacienda no disponible. La invalidación quedó pendiente."

    if response.status_code >= 500:
        invalidation.response_payload = {
            "success": None,
            "error": {
                "type": "api_unavailable",
                "message": response.text,
                "status_code": response.status_code,
            },
        }
        invalidation.status = DTEInvalidation.PENDING
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.error_message = response.text
        invalidation.error_code = str(response.status_code)
        invalidation.processed_at = timezone.now()
        invalidation.save(
            update_fields=[
                "response_payload",
                "status",
                "hacienda_state",
                "error_message",
                "error_code",
                "processed_at",
            ]
        )
        return invalidation, "Hacienda no disponible. La invalidación quedó pendiente."

    try:
        response_data = response.json()
    except ValueError:
        response_data = {"raw_text": response.text}

    invalidation.response_payload = response_data
    estado_interno, estado_hacienda, user_message = interpret_dte_response(response_data)
    invalidation.hacienda_state = estado_hacienda
    invalidation.status = estado_interno
    invalidation.processed_at = timezone.now()
    invalidation.save(
        update_fields=[
            "response_payload",
            "status",
            "hacienda_state",
            "processed_at",
        ]
    )

    if estado_interno == DTEInvalidation.ACCEPTED:
        invoice.dte_status = Invoice.INVALIDATED
        invoice.save(update_fields=["dte_status"])

    return invalidation, user_message
