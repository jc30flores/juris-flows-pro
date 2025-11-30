export type StaffRole = "ADMIN" | "COLABORADOR" | "CONTADOR";

export interface StaffUser {
  id: number;
  name: string;
  email?: string | null;
  role: StaffRole;
  active: boolean;
}

export interface StaffUserPayload {
  name: string;
  email?: string | null;
  role: StaffRole;
  active?: boolean;
}
