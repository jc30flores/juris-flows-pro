export type ClientType = "CF" | "CCF" | "SX";

export interface Client {
  id: number;
  full_name: string;
  company_name?: string | null;
  client_type: ClientType;
  dui?: string | null;
  nit?: string | null;
  nrc?: string | null;
  phone?: string | null;
  email?: string | null;
  direccion?: string | null;
  department_code?: string | null;
  municipality_code?: string | null;
  activity_code?: string | null;
  activity_description?: string | null;
}

export interface ClientPayload {
  full_name: string;
  company_name?: string;
  client_type: ClientType;
  dui?: string;
  nit?: string;
  nrc?: string;
  phone?: string;
  email?: string;
  direccion?: string;
  department_code?: string | null;
  municipality_code?: string | null;
  activity_code?: string | null;
  activity_description?: string | null;
}
