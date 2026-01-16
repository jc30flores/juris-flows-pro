export interface ServiceCategory {
  id: number;
  name: string;
  description?: string;
  active: boolean;
}

export interface Service {
  id: number;
  code: string;
  name: string;
  category: number | ServiceCategory;
  unit_price: number | string;
  wholesale_price?: number | string | null;
  active: boolean;
}

export interface ServicePayload {
  code: string;
  name: string;
  category: number;
  unit_price: number;
  wholesale_price?: number | null;
  active: boolean;
}
