export type InvoiceDocType = "CF" | "CCF" | "SX";

export type PaymentMethod = "Efectivo" | "Tarjeta" | "Transferencia" | "Cheque";

export type DteStatus =
  | "Aprobado"
  | "Pendiente"
  | "Rechazado"
  | "ACEPTADO"
  | "RECHAZADO"
  | "ERROR"
  | "INVALIDADO"
  | "Invalidado";

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
  dte_codigo_generacion?: string | null;
  dte_numero_control?: string | null;
  dte_generation_code?: string;
  hacienda_uuid?: string;
  dte_uuid?: string;
  has_credit_note?: boolean;
  credit_note_status?: string | null;
  dte?: {
    codigoGeneracion?: string;
    codigo_generacion?: string;
    uuid?: string;
  };
  dte_records?: Array<{
    dte_type?: string;
    status?: string;
    hacienda_state?: string;
    control_number?: string;
    issue_date?: string;
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
