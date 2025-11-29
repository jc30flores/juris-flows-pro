export type ClientType = "CF" | "CCF" | "SX";

export interface Client {
  id: number;
  full_name: string;
  company_name?: string | null;
  client_type: ClientType;
  dui?: string | null;
  nit?: string | null;
  phone?: string | null;
  email?: string | null;
  nrc?: string | null;
  giro?: string | null;
  direccion?: string | null;
}

export interface ClientPayload {
  full_name: string;
  company_name?: string;
  client_type: ClientType;
  dui?: string;
  nit?: string;
  phone?: string;
  email?: string;
}
