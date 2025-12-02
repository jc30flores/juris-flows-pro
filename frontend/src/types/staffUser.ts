export type StaffRole = "ADMIN" | "COLABORADOR" | "CONTADOR";

export interface StaffUser {
  id: number;
  full_name: string;
  username: string;
  role: StaffRole;
  is_active: boolean;
}

export interface StaffUserPayload {
  full_name: string;
  username: string;
  password?: string;
  role: StaffRole;
  is_active?: boolean;
}
