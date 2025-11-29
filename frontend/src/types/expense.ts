export interface Expense {
  id: number;
  name: string;
  provider: string;
  date: string;
  total: number | string;
  created_at?: string;
}

export interface ExpensePayload {
  name: string;
  provider: string;
  date: string;
  total: number;
}
