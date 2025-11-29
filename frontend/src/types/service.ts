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
  category: number;
  base_price: number | string;
  active: boolean;
}

export interface ServicePayload {
  code: string;
  name: string;
  category: number;
  base_price: number;
  active: boolean;
}
