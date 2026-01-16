import { Client } from "./client";
import { Service } from "./service";

export type InvoiceDocType = "CF" | "CCF" | "SX";

export type PaymentMethod = "Efectivo" | "Tarjeta" | "Transferencia" | "Cheque";

export type DteStatus =
  | "ACEPTADO"
  | "PENDIENTE"
  | "RECHAZADO"
  | "ERROR"
  | "Aprobado"
  | "Pendiente"
  | "Rechazado";

export interface InvoiceItem {
  id: number;
  invoice: number;
  service: number | Service;
  quantity: number;
  unit_price_snapshot?: number | string;
  wholesale_price_snapshot?: number | string | null;
  price_type?: "UNIT" | "WHOLESALE";
  applied_unit_price?: number | string;
  unit_price: number | string;
  line_subtotal?: number | string;
  subtotal: number | string;
  price_overridden?: boolean;
}

export interface Invoice {
  id: number;
  number: string;
  date: string;
  date_display?: string;
  issue_date?: string;
  client: number | Client;
  doc_type: InvoiceDocType;
  tipo?: string;
  type?: string;
  dte_tipo?: string;
  dte?: {
    tipoDte?: string;
    tipo?: string;
    codigoGeneracion?: string;
    identificacion?: {
      codigoGeneracion?: string;
      codigo_generacion?: string;
      numeroControl?: string;
      numero_control?: string;
    };
  };
  codigo_generacion?: string;
  codigoGeneracion?: string;
  numero_control?: string;
  numeroControl?: string;
  payment_method: PaymentMethod;
  dte_status: DteStatus;
  dte_message?: string;
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
  unit_price_snapshot?: number;
  wholesale_price_snapshot?: number | null;
  applied_unit_price?: number;
  price_type?: "UNIT" | "WHOLESALE";
  price_overridden?: boolean;
  line_subtotal?: number;
  subtotal: number;
}

export interface SelectedServicePayload {
  service_id: number;
  name: string;
  price: number;
  unit_price_snapshot?: number;
  wholesale_price_snapshot?: number | null;
  unit_price?: number;
  applied_unit_price?: number;
  price_type?: "UNIT" | "WHOLESALE";
  price_overridden?: boolean;
  quantity: number;
  line_subtotal?: number;
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
  override_token?: string;
}
