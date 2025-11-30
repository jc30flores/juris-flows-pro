export type InvoiceDocType = "CF" | "CCF" | "SX";

export type PaymentMethod = "Efectivo" | "Tarjeta" | "Transferencia" | "Cheque";

export type DteStatus = "Aprobado" | "Pendiente" | "Rechazado";

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

export interface InvoicePayload {
  date: string;
  client: number;
  doc_type: InvoiceDocType;
  payment_method: PaymentMethod;
  total: number;
  items: InvoiceItemPayload[];
}
