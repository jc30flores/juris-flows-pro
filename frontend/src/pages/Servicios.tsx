import { useEffect, useMemo, useState } from "react";
import { Plus, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { NuevoServicioModal } from "@/components/modals/NuevoServicioModal";
import { EditarServicioModal } from "@/components/modals/EditarServicioModal";
import { NuevaCategoriaModal } from "@/components/modals/NuevaCategoriaModal";
import { api } from "@/lib/api";
import {
  Service,
  ServiceCategory,
  ServicePayload,
} from "@/types/service";

export default function Servicios() {
  const [modoEdicion, setModoEdicion] = useState(false);
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const [showEditarModal, setShowEditarModal] = useState(false);
  const [showCategoriaModal, setShowCategoriaModal] = useState(false);
  const [servicioSeleccionado, setServicioSeleccionado] = useState<Service | null>(
    null,
  );
  const [services, setServices] = useState<Service[]>([]);
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const fetchServices = async () => {
    setLoading(true);
    setError("");
    try {
      const [servicesResponse, categoriesResponse] = await Promise.all([
        api.get<Service[]>("/services/"),
        api.get<ServiceCategory[]>("/service-categories/"),
      ]);
      setServices(servicesResponse.data);
      setCategories(categoriesResponse.data);
    } catch (err) {
      console.error("Error al cargar servicios", err);
      setError("No se pudieron cargar los servicios");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateService = async (payload: ServicePayload) => {
    await api.post("/services/", payload);
    await fetchServices();
  };

  const handleUpdateService = async (id: number, payload: Partial<ServicePayload>) => {
    await api.patch(`/services/${id}/`, payload);
    await fetchServices();
  };

  const handleDeleteService = async (id: number) => {
    await api.delete(`/services/${id}/`);
    setServices((prev) => prev.filter((service) => service.id !== id));
  };

  useEffect(() => {
    fetchServices();
  }, []);

  const categoryLookup = useMemo(() => {
    return categories.reduce<Record<number, string>>((acc, category) => {
      acc[category.id] = category.name;
      return acc;
    }, {});
  }, [categories]);

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      {/* Título móvil */}
      <h2 className="text-lg font-semibold md:hidden">Servicios</h2>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-end gap-3 md:gap-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="modo-edicion"
            checked={modoEdicion}
            onCheckedChange={setModoEdicion}
          />
          <Label htmlFor="modo-edicion" className="cursor-pointer">
            Modo Edición
          </Label>
        </div>
        {modoEdicion && (
          <div className="flex gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              className="flex-1 sm:flex-initial"
              onClick={() => setShowCategoriaModal(true)}
            >
              <Tag className="h-4 w-4 mr-2" />
              <span className="md:hidden">Categoría</span>
              <span className="hidden md:inline">Nueva Categoría</span>
            </Button>
            <Button
              className="bg-primary hover:bg-primary/90 flex-1 sm:flex-initial"
              onClick={() => setShowNuevoModal(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              <span className="md:hidden">Servicio</span>
              <span className="hidden md:inline">Nuevo Servicio</span>
            </Button>
          </div>
        )}
      </div>

      {/* Tabla de Servicios */}
      <div className="rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          {loading && (
            <div className="p-4 text-sm text-muted-foreground">Cargando servicios...</div>
          )}
          {error && !loading && (
            <div className="p-4 text-sm text-destructive">{error}</div>
          )}
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-sm font-medium">Código</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Servicio</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Categoría</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Precio Base</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {!loading &&
                services.map((servicio) => (
                  <tr
                    key={servicio.id}
                    onClick={() => {
                      if (modoEdicion) {
                        setServicioSeleccionado(servicio);
                        setShowEditarModal(true);
                      }
                    }}
                    className={`border-b border-border hover:bg-muted/30 transition-colors ${
                      modoEdicion ? "cursor-pointer" : ""
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-sm">{servicio.code}</td>
                    <td className="px-4 py-3 font-medium">{servicio.name}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {categoryLookup[servicio.category] || "Sin categoría"}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-accent">
                      ${Number(servicio.base_price).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <Badge
                        variant={servicio.active ? "default" : "secondary"}
                        className="text-xs"
                      >
                        {servicio.active ? "Activo" : "Inactivo"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              {!loading && services.length === 0 && (
                <tr>
                  <td
                    className="px-4 py-3 text-sm text-muted-foreground"
                    colSpan={5}
                  >
                    No hay servicios registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <NuevoServicioModal
        open={showNuevoModal}
        onOpenChange={setShowNuevoModal}
        categories={categories}
        onSubmit={async (payload) => {
          await handleCreateService(payload);
          setShowNuevoModal(false);
        }}
      />
      <EditarServicioModal
        open={showEditarModal}
        onOpenChange={setShowEditarModal}
        servicio={servicioSeleccionado}
        categories={categories}
        onSubmit={async (payload) => {
          if (!servicioSeleccionado) return;
          await handleUpdateService(servicioSeleccionado.id, payload);
          setShowEditarModal(false);
        }}
        onDelete={async () => {
          if (!servicioSeleccionado) return;
          await handleDeleteService(servicioSeleccionado.id);
          setShowEditarModal(false);
        }}
      />
      <NuevaCategoriaModal
        open={showCategoriaModal}
        onOpenChange={setShowCategoriaModal}
      />
    </div>
  );
}
