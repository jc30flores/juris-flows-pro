import logging
import random
import uuid
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.utils import timezone

from .models import DTERecord, InvoiceItem, Service

logger = logging.getLogger(__name__)


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


def send_cf_dte_for_invoice(invoice) -> DTERecord:
    """
    Construye el JSON DTE para tipo CF a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    codigo_generacion = str(uuid.uuid4()).upper()
    random_suffix = "".join(str(random.randint(0, 9)) for _ in range(15))
    numero_control = f"DTE-01-M002P001-{random_suffix}"

    now = timezone.localtime()
    fec_emi = invoice.date.isoformat()
    hor_emi = now.strftime("%H:%M:%S")

    receptor, receiver_nit, receiver_name = _build_receptor(invoice)
    items: list[InvoiceItem] = list(invoice.items.select_related("service"))

    cuerpo_documento = []
    total_gravada = Decimal("0.00")
    total_iva = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        unit_price = _to_decimal(item.unit_price)
        quantity = Decimal(item.quantity)
        venta_gravada = _to_decimal(item.subtotal if item.subtotal else unit_price * quantity)
        iva_item = _to_decimal(venta_gravada * Decimal("0.13"))

        total_gravada += venta_gravada
        total_iva += iva_item

        service: Service | None = getattr(item, "service", None)
        descripcion = service.name if service else "Servicio"
        codigo = service.code if service and service.code else "SERV"

        cuerpo_documento.append(
            {
                "ventaExenta": 0,
                "uniMedida": 59,
                "cantidad": float(quantity),
                "noGravado": 0,
                "ivaItem": _format_currency(iva_item),
                "numeroDocumento": None,
                "codigo": codigo,
                "ventaGravada": _format_currency(venta_gravada),
                "codTributo": None,
                "numItem": index,
                "psv": 0,
                "ventaNoSuj": 0,
                "precioUni": _format_currency(unit_price),
                "montoDescu": 0,
                "tributos": None,
                "descripcion": descripcion,
                "tipoItem": 1,
            }
        )

    sub_total = total_gravada
    monto_total_operacion = sub_total + total_iva
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
                "montoPago": _format_currency(total_pagar),
            }
        ],
        "porcentajeDescuento": 0,
        "saldoFavor": 0,
        "totalNoGravado": 0,
        "totalGravada": _format_currency(total_gravada),
        "descuExenta": 0,
        "subTotal": _format_currency(sub_total),
        "totalLetras": f"{_format_currency(total_pagar)} DOLARES",
        "descuNoSuj": 0,
        "subTotalVentas": _format_currency(sub_total),
        "reteRenta": 0,
        "tributos": None,
        "totalNoSuj": 0,
        "montoTotalOperacion": _format_currency(monto_total_operacion),
        "totalIva": _format_currency(total_iva),
        "descuGravada": 0,
        "totalExenta": 0,
        "condicionOperacion": 1,
        "totalPagar": _format_currency(total_pagar),
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
                "ambiente": "00",
                "numeroControl": numero_control,
                "horEmi": hor_emi,
                "tipoOperacion": 1,
                "tipoMoneda": "USD",
            },
            "resumen": resumen,
            "extension": {
                "observaciones": observaciones,
                "placaVehiculo": None,
                "docuRecibe": None,
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

    url = "https://t12101304761012.cheros.dev/api/v1/dte/factura"
    headers = {
        "Authorization": "Bearer api_k_12101304761012",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        try:
            response_data = response.json()
        except ValueError:
            response_data = {"raw_text": response.text}

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        record.hacienda_state = response_data.get("estado", "") if isinstance(response_data, dict) else ""
        record.status = "ACEPTADO" if response.ok else "RECHAZADO"
        record.save()
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending CF DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "ERROR"
        record.hacienda_state = "ERROR"
        record.save()
        return record
