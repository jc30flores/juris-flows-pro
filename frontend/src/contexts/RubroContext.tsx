import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type { ActiveRubroResponse, Rubro, RubrosResponse } from "@/types/issuer";
import { useAuth } from "@/contexts/AuthContext";

interface RubroContextValue {
  rubros: Rubro[];
  activeRubro: Rubro | null;
  loading: boolean;
  refreshRubros: () => Promise<void>;
  setActiveRubro: (rubroCode: string) => Promise<void>;
}

const RubroContext = createContext<RubroContextValue | undefined>(undefined);

export const RubroProvider = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  const [rubros, setRubros] = useState<Rubro[]>([]);
  const [activeRubro, setActiveRubroState] = useState<Rubro | null>(null);
  const [loading, setLoading] = useState(false);

  const syncActiveRubro = (data: RubrosResponse) => {
    setRubros(data.rubros);
    const match = data.rubros.find((rubro) => rubro.code === data.active_rubro_code);
    if (match) {
      setActiveRubroState(match);
    } else if (data.active_rubro_code) {
      setActiveRubroState({
        code: data.active_rubro_code,
        name: data.active_rubro_name || data.active_rubro_code,
      });
    } else {
      setActiveRubroState(null);
    }
  };

  const refreshRubros = async () => {
    if (!user) {
      setRubros([]);
      setActiveRubroState(null);
      return;
    }
    setLoading(true);
    try {
      const response = await api.get<RubrosResponse>("/emisor/rubros/");
      syncActiveRubro(response.data);
    } catch (error) {
      console.error("Error al cargar rubros", error);
    } finally {
      setLoading(false);
    }
  };

  const setActiveRubro = async (rubroCode: string) => {
    if (!user) return;
    const response = await api.post<ActiveRubroResponse>("/emisor/active-rubro/", {
      rubro_code: rubroCode,
    });
    const rubroName = response.data.active_rubro_name || "";
    setActiveRubroState({ code: response.data.active_rubro_code, name: rubroName });
  };

  useEffect(() => {
    void refreshRubros();
  }, [user]);

  const value = useMemo(
    () => ({ rubros, activeRubro, loading, refreshRubros, setActiveRubro }),
    [rubros, activeRubro, loading],
  );

  return <RubroContext.Provider value={value}>{children}</RubroContext.Provider>;
};

export const useRubro = () => {
  const ctx = useContext(RubroContext);
  if (!ctx) {
    throw new Error("useRubro must be used within a RubroProvider");
  }
  return ctx;
};
