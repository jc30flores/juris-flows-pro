export type Rubro = {
  code: string;
  name: string;
};

export type RubrosResponse = {
  rubros: Rubro[];
  active_rubro_code: string;
  active_rubro_name: string;
};

export type ActiveRubroResponse = {
  ok?: boolean;
  active_rubro_code: string;
  active_rubro_name: string;
};
