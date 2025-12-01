import json
import logging
import random
import uuid
from decimal import Decimal, ROUND_HALF_UP

import requests
from django.utils import timezone

from .models import DTERecord, InvoiceItem, Service

logger = logging.getLogger(__name__)


IVA_RATE = Decimal("0.13")
ONE = Decimal("1")


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
        unit_price = Decimal(str(item.unit_price))
        quantity = Decimal(str(item.quantity))
        gross_line = quantity * unit_price

        base_line, iva_line = split_gross_amount_with_tax(gross_line)

        total_gravada += base_line
        total_iva += iva_line

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
                "ventaGravada": float(_round_2(base_line)),
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

    total_gravada = _round_2(total_gravada)
    total_iva = _round_2(total_iva)
    monto_total_operacion = _round_2(total_gravada + total_iva)
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
        "totalGravada": float(total_gravada),
        "descuExenta": 0,
        "subTotal": float(total_gravada),
        "totalLetras": f"{float(total_pagar)} DOLARES",
        "descuNoSuj": 0,
        "subTotalVentas": float(total_gravada),
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

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

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


def send_ccf_dte_for_invoice(invoice) -> DTERecord:
    """
    Construye el JSON DTE para tipo CCF (03) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    codigo_generacion = str(uuid.uuid4()).upper()
    random_suffix = "".join(str(random.randint(0, 9)) for _ in range(15))
    numero_control = f"DTE-03-M002P001-{random_suffix}"

    now = timezone.localtime()
    fec_emi = invoice.date.isoformat()
    hor_emi = now.strftime("%H:%M:%S")

    client = getattr(invoice, "client", None)
    emitter_address = EMITTER_INFO["direccion"]

    client_name = (client.company_name if client else "") or (client.full_name if client else "") or "CLIENTE"
    client_trade_name = client.company_name if client and client.company_name else client_name
    client_nit = (client.nit if client else "") or ""
    client_nrc = getattr(client, "nrc", "") or ""
    client_phone = (client.phone if client else "") or "00000000"
    client_email = (client.email if client else "") or None
    client_cod_act = getattr(client, "activity_code", None)
    client_desc_act = getattr(client, "activity_description", None)

    client_address = {
        "municipio": (client.municipality_code if client else None)
        or emitter_address.get("municipio", "22"),
        "complemento": emitter_address.get("complemento", ""),
        "departamento": (client.department_code if client else None)
        or emitter_address.get("departamento", "12"),
    }

    receptor = {
        "nombre": client_name,
        "nombreComercial": client_trade_name,
        "direccion": client_address,
        "correo": client_email,
        "nit": client_nit,
        "nrc": client_nrc,
        "telefono": client_phone,
        "codActividad": client_cod_act,
        "descActividad": client_desc_act,
    }

    items: list[InvoiceItem] = list(invoice.items.select_related("service"))
    cuerpo_documento = []
    total_gravada = Decimal("0.00")
    total_iva = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        unit_price = Decimal(str(item.unit_price))
        quantity = Decimal(str(item.quantity))
        gross_line = quantity * unit_price
        line_base, iva_line = split_gross_amount_with_tax(gross_line)

        total_gravada += line_base
        total_iva += iva_line

        service: Service | None = getattr(item, "service", None)
        descripcion = service.name if service else "Servicio"
        codigo = service.code if service and service.code else "SERVICIO"

        cuerpo_documento.append(
            {
                "ventaExenta": 0,
                "numItem": index,
                "tipoItem": 1,
                "codigo": codigo,
                "cantidad": float(quantity),
                "tributos": ["20"],
                "uniMedida": 59,
                "noGravado": 0,
                "codTributo": None,
                "montoDescu": 0,
                "ventaNoSuj": 0,
                "psv": 0,
                "precioUni": float(_round_2(unit_price)),
                "descripcion": descripcion,
                "ventaGravada": float(_round_2(line_base)),
                "numeroDocumento": None,
            }
        )

    total_gravada = _round_2(total_gravada)
    total_iva = _round_2(total_iva)
    total_operacion = _round_2(total_gravada + total_iva)
    total_letras = f"{float(total_operacion)} DOLARES"

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
        "totalGravada": float(total_gravada),
        "descuExenta": 0,
        "subTotal": float(total_gravada),
        "totalLetras": total_letras,
        "descuNoSuj": 0,
        "subTotalVentas": float(total_gravada),
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
            "emisor": {**EMITTER_INFO},
            "documentoRelacionado": None,
            "ventaTercero": None,
            "otrosDocumentos": None,
            "receptor": receptor,
        }
    }

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

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        record.hacienda_state = response_data.get("estado", "") if isinstance(response_data, dict) else ""
        record.status = "ACEPTADO" if response.ok else "RECHAZADO"
        record.save()
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending CCF DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "ERROR"
        record.hacienda_state = "ERROR"
        record.save()
        return record


def send_se_dte_for_invoice(invoice) -> DTERecord:
    """
    Construye el JSON DTE para tipo Sujeto Excluido (14) a partir de la factura y sus items,
    lo envía al endpoint externo y registra el request/response en DTERecord.
    """

    codigo_generacion = str(uuid.uuid4()).upper()
    random_suffix = "".join(str(random.randint(0, 9)) for _ in range(15))
    numero_control = f"DTE-14-M002P001-{random_suffix}"

    now = timezone.localtime()
    fec_emi = invoice.date.isoformat()
    hor_emi = now.strftime("%H:%M:%S")

    client = getattr(invoice, "client", None)
    se_tipo_documento = "13"
    se_nombre = (client.company_name if client else "") or (client.full_name if client else "") or "CONSUMIDOR FINAL"
    se_telefono = (client.phone if client else None) or "00000000"
    se_num_documento = (
        getattr(client, "dui", None)
        or getattr(client, "nit", None)
        or getattr(client, "document", None)
        or "000000000"
    )
    se_correo = getattr(client, "email", None)
    se_cod_actividad = getattr(client, "activity_code", None)
    se_desc_actividad = getattr(client, "activity_description", None)
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
        "totalLetras": f"{_format_currency(total_pagar)} DOLARES",
        "totalCompra": _format_currency(total_compra),
        "totalPagar": _format_currency(total_pagar),
    }

    payload = {
        "dte": {
            "apendice": None,
            "cuerpoDocumento": cuerpo_documento,
            "resumen": resumen,
            "sujetoExcluido": sujeto_excluido,
            "emisor": {**EMITTER_INFO},
            "identificacion": {
                "codigoGeneracion": codigo_generacion,
                "motivoContin": None,
                "fecEmi": fec_emi,
                "tipoModelo": 1,
                "tipoDte": "14",
                "version": 1,
                "tipoContingencia": None,
                "ambiente": "00",
                "numeroControl": numero_control,
                "horEmi": hor_emi,
                "tipoOperacion": 1,
                "tipoMoneda": "USD",
            },
        }
    }

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

        print("\nJSON API RESPUESTA:\n")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))

        record.response_payload = response_data
        record.hacienda_uuid = response_data.get("uuid", "") if isinstance(response_data, dict) else ""
        record.hacienda_state = response_data.get("estado", "") if isinstance(response_data, dict) else ""
        record.status = "ACEPTADO" if response.ok else "RECHAZADO"
        record.save()
        return record
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error sending SE DTE", exc_info=exc)
        record.response_payload = {"error": str(exc)}
        record.status = "ERROR"
        record.hacienda_state = "ERROR"
        record.save()
        return record
