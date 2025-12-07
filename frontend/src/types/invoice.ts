export type InvoiceDocType = "CF" | "CCF" | "SX";

export type PaymentMethod = "Efectivo" | "Tarjeta" | "Transferencia" | "Cheque";

export type DteStatus =
  | "Aprobado"
  | "Pendiente"
  | "Rechazado"
  | "ACEPTADO"
  | "RECHAZADO"
  | "ERROR";

export interface InvoiceItem {
  id: number;
  invoice: number;
  service: number;
  quantity: number;
  unit_price: number | string;
  subtotal: number | string;
}

export interface Invoice {
  id: number;
  number: string;
  date: string;
  client: number;
  doc_type: InvoiceDocType;
  payment_method: PaymentMethod;
  dte_status: DteStatus;
  dte_message?: string;
  dte_generation_code?: string;
  hacienda_uuid?: string;
  dte_uuid?: string;
  dte?: {
    codigoGeneracion?: string;
    codigo_generacion?: string;
    uuid?: string;
  };
  dte_records?: Array<{
    codigoGeneracion?: string;
    codigo_generacion?: string;
    hacienda_uuid?: string;
    uuid?: string;
    response_payload?: Record<string, unknown>;
  }>;
  observations?: string;
  total: number | string;
  created_at: string;
  updated_at: string;
  items?: InvoiceItem[];
}

export interface InvoiceItemPayload {
  service: number;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface SelectedServicePayload {
  service_id: number;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
}

export interface InvoicePayload {
  date: string;
  client: number;
  doc_type: InvoiceDocType;
  payment_method: PaymentMethod;
  total: number;
  observations?: string;
  services: SelectedServicePayload[];
}
