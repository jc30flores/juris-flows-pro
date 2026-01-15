import json
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .dte_cf_service import interpret_dte_response, _resolve_emitter_info
from .models import DTEInvalidation, DTERecord, Invoice, StaffUser


DEFAULT_INVALIDATION_URL = (
    getattr(settings, "API_DTE_INVALIDATION_URL", None)
    or getattr(settings, "DTE_INVALIDATION_URL", None)
    or "https://p12172402231026.cheros.dev/api/v1/dte/invalidacion"
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


def _extract_receptor(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    dte_payload = payload.get("dte")
    if isinstance(dte_payload, dict):
        receptor = dte_payload.get("receptor")
        if isinstance(receptor, dict):
            return receptor
    return {}


def _format_date(value) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _s(value) -> str:
    return str(value or "").strip()


def _mask_headers(headers: dict) -> dict:
    masked = {}
    for key, value in (headers or {}).items():
        if key.lower() == "authorization" and value:
            masked[key] = "Bearer ***"
        else:
            masked[key] = value
    return masked


def _truncate(value: str, limit: int = 2000) -> str:
    if value is None:
        return ""
    value_str = str(value)
    if len(value_str) <= limit:
        return value_str
    return f"{value_str[:limit]}... (truncado)"


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
    if not codigo_original or not numero_control:
        raise ValueError("Faltan datos mínimos del DTE para invalidar.")
    tipo_dte = _resolve_tipo_dte(invoice, ident)
    if not tipo_dte:
        raise ValueError("No se pudo identificar el tipo de DTE para invalidación.")
    fec_emi = ident.get("fecEmi") or ident.get("fec_emi") or _format_date(invoice.date)
    monto_iva_raw = resumen.get("totalIva") or resumen.get("total_iva")
    monto_iva = (
        Decimal(str(monto_iva_raw)) if monto_iva_raw not in (None, "") else Decimal("0")
    )

    receptor_payload = _extract_receptor(record.request_payload or {})
    receptor_nombre = _s(receptor_payload.get("nombre")) or "CONSUMIDOR FINAL FRECUENTE"
    receptor_doc = (
        _s(receptor_payload.get("numDocumento"))
        or _s(receptor_payload.get("nit"))
        or _s(receptor_payload.get("dui"))
        or "00000000-0"
    )
    receptor_tipo_doc = _s(receptor_payload.get("tipoDocumento")) or "13"
    receptor_telefono = _s(receptor_payload.get("telefono")) or "77777777"
    receptor_correo = _s(receptor_payload.get("correo")) or "facturacioncji@gmail.com"

    now_local = timezone.localtime()
    codigo_generacion = str(uuid.uuid4()).upper()
    ambiente = ident.get("ambiente") or "01"

    emitter_info, _, _ = _resolve_emitter_info(staff_user)
    emisor_nombre = _s(emitter_info.get("nombre"))
    emisor_nombre_comercial = _s(emitter_info.get("nombreComercial"))
    emisor_nit = _s(emitter_info.get("nit"))
    emisor_telefono = _s(emitter_info.get("telefono"))
    emisor_correo = _s(emitter_info.get("correo"))
    nom_establecimiento = (
        _s(emitter_info.get("nomEstablecimiento"))
        or emisor_nombre_comercial
        or emisor_nombre
    )
    responsable_nombre = (
        _s(getattr(staff_user, "full_name", None))
        or _s(getattr(staff_user, "username", None))
        or emisor_nombre
    )
    responsable_doc = emisor_nit or "00000000-0"
    motivo_anulacion_text = _s(motivo_anulacion) or "Rescindir de la operación realizada"
    motivo_payload = {
        "tipoAnulacion": int(tipo_anulacion or 2),
        "motivoAnulacion": motivo_anulacion_text,
        "nombreResponsable": responsable_nombre,
        "tipDocResponsable": "36",
        "numDocResponsable": responsable_doc,
        "nombreSolicita": responsable_nombre,
        "tipDocSolicita": "36",
        "numDocSolicita": responsable_doc,
    }

    payload = {
        "invalidacion": {
            "identificacion": {
                "version": 2,
                "ambiente": ambiente,
                "codigoGeneracion": codigo_generacion,
                "fecAnula": now_local.strftime("%Y-%m-%d"),
                "horAnula": now_local.strftime("%H:%M:%S"),
            },
            "emisor": {
                **emitter_info,
                "nit": emisor_nit,
                "nombre": emisor_nombre,
                "tipoEstablecimiento": _s(emitter_info.get("tipoEstablecimiento")),
                "nomEstablecimiento": nom_establecimiento,
                "codEstableMH": _s(emitter_info.get("codEstableMH")),
                "codEstable": _s(emitter_info.get("codEstable")),
                "codPuntoVentaMH": _s(emitter_info.get("codPuntoVentaMH")),
                "codPuntoVenta": _s(emitter_info.get("codPuntoVenta")),
                "telefono": emisor_telefono,
                "correo": emisor_correo,
            },
            "documento": {
                "tipoDte": tipo_dte,
                "codigoGeneracion": codigo_original,
                "numeroControl": numero_control,
                "selloRecibido": sello_recibido,
                "fecEmi": fec_emi,
                "montoIva": float(monto_iva),
                "codigoGeneracionR": None,
                "tipoDocumento": receptor_tipo_doc,
                "numDocumento": receptor_doc,
                "nombre": receptor_nombre,
                "telefono": receptor_telefono,
                "correo": receptor_correo,
            },
            "motivo": motivo_payload,
        }
    }
    motivo_payload = payload["invalidacion"].get("motivo") or {}
    emisor_payload = payload["invalidacion"].get("emisor") or {}
    fallback_name = (
        _s(getattr(staff_user, "full_name", None))
        or _s(getattr(staff_user, "username", None))
        or _s(emisor_payload.get("nombre"))
        or "EMISOR"
    )
    fallback_doc = (
        _s(motivo_payload.get("numDocSolicita"))
        or _s(emisor_payload.get("nit"))
        or "00000000-0"
    )
    fallback_doc_type = (
        _s(motivo_payload.get("tipDocSolicita"))
        or "36"
    )
    solicita_nombre = _s(motivo_payload.get("nombreSolicita")) or fallback_name
    solicita_tipo_doc = _s(motivo_payload.get("tipDocSolicita")) or fallback_doc_type
    solicita_num_doc = _s(motivo_payload.get("numDocSolicita")) or fallback_doc
    responsable_nombre = _s(motivo_payload.get("nombreResponsable")) or solicita_nombre
    responsable_tipo_doc = _s(motivo_payload.get("tipDocResponsable")) or solicita_tipo_doc
    responsable_num_doc = _s(motivo_payload.get("numDocResponsable")) or solicita_num_doc

    invalidation = DTEInvalidation.objects.create(
        invoice=invoice,
        dte_record=record,
        requested_by=staff_user,
        status=DTEInvalidation.SENDING,
        codigo_generacion=_s(codigo_generacion),
        tipo_anulacion=int(tipo_anulacion or 2),
        motivo_anulacion=motivo_anulacion_text,
        solicita_nombre=solicita_nombre,
        solicita_tipo_doc=solicita_tipo_doc,
        solicita_num_doc=solicita_num_doc,
        responsable_nombre=responsable_nombre,
        responsable_tipo_doc=responsable_tipo_doc,
        responsable_num_doc=responsable_num_doc,
        original_codigo_generacion=_s(codigo_original),
        original_numero_control=_s(numero_control),
        original_sello_recibido=_s(sello_recibido),
        original_tipo_dte=_s(tipo_dte),
        original_fec_emi=_s(fec_emi),
        original_monto_iva=monto_iva,
        request_payload=payload,
        hacienda_state="",
        sent_at=timezone.now(),
    )

    headers = {
        "Authorization": "Bearer api_key_cliente_12172402231026",
        "Content-Type": "application/json",
    }
    target_url = url or DEFAULT_INVALIDATION_URL
    if not target_url:
        raise ValueError("No se configuró el endpoint de invalidación.")

    print(f"[INVALIDATION] invoice_id={invoice.id}")
    print(f"[INVALIDATION] url={target_url}")
    print(f"[INVALIDATION] headers={_mask_headers(headers)}")
    print("[INVALIDATION] payload=")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        response = requests.post(target_url, json=payload, headers=headers, timeout=30)
        print(f"[INVALIDATION] http_status={response.status_code}")
        print(f"[INVALIDATION] http_text={_truncate(response.text)}")
    except requests.RequestException as exc:
        print(f"[INVALIDATION] request_exception={repr(exc)}")
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
        invalidation.status = DTEInvalidation.REJECTED
        invalidation.hacienda_state = "SIN_RESPUESTA"
        invalidation.error_message = response.text
        invalidation.error_code = f"bridge_{response.status_code}"
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
        return (
            invalidation,
            "Error interno del puente de Hacienda. Intente nuevamente más tarde.",
        )

    try:
        response_data = response.json()
    except ValueError:
        response_data = {"raw_text": response.text}

    if 400 <= response.status_code < 500:
        hacienda_resp = _extract_hacienda_response(response_data)
        estado_hacienda = (
            hacienda_resp.get("estado", "RECHAZADO")
            if isinstance(hacienda_resp, dict)
            else "RECHAZADO"
        )
        descripcion = ""
        if isinstance(hacienda_resp, dict):
            descripcion = hacienda_resp.get("descripcionMsg") or ""
        error_payload = response_data.get("error") if isinstance(response_data, dict) else {}
        if isinstance(error_payload, dict) and not descripcion:
            descripcion = error_payload.get("message") or ""
        descripcion = descripcion or _truncate(response.text)
        invalidation.response_payload = response_data
        invalidation.status = DTEInvalidation.REJECTED
        invalidation.hacienda_state = estado_hacienda
        invalidation.error_message = descripcion
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
        return invalidation, f"Invalidación rechazada: {descripcion}"

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
