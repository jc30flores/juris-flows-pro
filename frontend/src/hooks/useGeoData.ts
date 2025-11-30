import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { Activity } from "@/types/activity";
import { Department, Municipality } from "@/types/geo";

interface GeoDataState {
  departments: Department[];
  municipalities: Municipality[];
  activities: Activity[];
  loading: boolean;
  error: string | null;
}

export function useGeoData() {
  const [state, setState] = useState<GeoDataState>({
    departments: [],
    municipalities: [],
    activities: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    let active = true;

    const loadData = async () => {
      try {
        const [deptRes, muniRes, actRes] = await Promise.all([
          api.get<Department[]>("/geo/departments/"),
          api.get<Municipality[]>("/geo/municipalities/"),
          api.get<Activity[]>("/activities/"),
        ]);

        if (!active) return;

        setState({
          departments: deptRes.data,
          municipalities: muniRes.data,
          activities: actRes.data,
          loading: false,
          error: null,
        });
      } catch (error) {
        console.error("Error loading geo data", error);
        if (!active) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: "No se pudieron cargar datos geográficos",
        }));
      }
    };

    loadData();

    return () => {
      active = false;
    };
  }, []);

  const getMunicipalitiesByDept = useMemo(
    () =>
      (deptCode?: string) =>
        state.municipalities.filter(
          (municipality) => !deptCode || municipality.dept_code === deptCode,
        ),
    [state.municipalities],
  );

  return {
    departments: state.departments,
    municipalities: state.municipalities,
    activities: state.activities,
    getMunicipalitiesByDept,
    loading: state.loading,
    error: state.error,
  };
}
