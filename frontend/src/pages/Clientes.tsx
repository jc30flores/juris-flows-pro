import { useEffect, useMemo, useState } from "react";
import { Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { NuevoClienteModal } from "@/components/modals/NuevoClienteModal";
import { EditarClienteModal } from "@/components/modals/EditarClienteModal";
import { api } from "@/lib/api";
import { Client, ClientPayload } from "@/types/client";

export default function Clientes() {
  const [modoEdicion, setModoEdicion] = useState(false);
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const [showEditarModal, setShowEditarModal] = useState(false);
  const [clienteSeleccionado, setClienteSeleccionado] = useState<Client | null>(
    null,
  );
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [search, setSearch] = useState("");

  const fetchClients = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<Client[]>("/clients/");
      setClients(response.data);
    } catch (err) {
      console.error("Error al cargar clientes", err);
      setError("No se pudieron cargar los clientes");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateClient = async (payload: ClientPayload) => {
    await api.post("/clients/", payload);
    await fetchClients();
  };

  const handleUpdateClient = async (
    id: number,
    payload: Partial<ClientPayload>,
  ) => {
    await api.patch(`/clients/${id}/`, payload);
    await fetchClients();
  };

  const handleDeleteClient = async (id: number) => {
    await api.delete(`/clients/${id}/`);
    setClients((prev) => prev.filter((client) => client.id !== id));
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const filteredClients = useMemo(() => {
    const query = search.toLowerCase();
    return clients.filter((client) => {
      return (
        client.full_name.toLowerCase().includes(query) ||
        (client.dui?.toLowerCase() || "").includes(query) ||
        (client.nit?.toLowerCase() || "").includes(query) ||
        (client.email?.toLowerCase() || "").includes(query) ||
        (client.phone?.toLowerCase() || "").includes(query) ||
        (client.company_name?.toLowerCase() || "").includes(query)
      );
    });
  }, [clients, search]);

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      {/* Título móvil */}
      <h2 className="text-lg font-semibold md:hidden">Clientes</h2>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-end gap-3 md:gap-4">
        <div className="flex items-center space-x-2">
          <Switch
            id="modo-edicion-clientes"
            checked={modoEdicion}
            onCheckedChange={setModoEdicion}
          />
          <Label htmlFor="modo-edicion-clientes" className="cursor-pointer">
            Modo Edición
          </Label>
        </div>
        {modoEdicion && (
          <Button 
            className="bg-primary hover:bg-primary/90 w-full md:w-auto"
            onClick={() => setShowNuevoModal(true)}
          >
            <Plus className="h-4 w-4 mr-2" />
            <span className="md:hidden">Nuevo</span>
            <span className="hidden md:inline">Nuevo Cliente</span>
          </Button>
        )}
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre, DUI, NIT..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {loading && (
          <div className="text-sm text-muted-foreground">Cargando clientes...</div>
        )}
        {error && !loading && (
          <div className="text-sm text-destructive">{error}</div>
        )}
        {!loading &&
          filteredClients.map((cliente) => (
          <div
            key={cliente.id}
            onClick={() => {
              if (modoEdicion) {
                setClienteSeleccionado(cliente);
                setShowEditarModal(true);
              }
            }}
            className={`rounded-lg border border-border bg-card p-4 shadow-elegant hover:shadow-elegant-lg transition-smooth ${
              modoEdicion ? "cursor-pointer" : ""
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <p className="font-semibold text-lg mb-1">{cliente.full_name}</p>
                {cliente.company_name && (
                  <p className="text-sm text-muted-foreground mb-2">
                    {cliente.company_name}
                  </p>
                )}
                <Badge
                  variant="outline"
                  className={
                    cliente.client_type === "CCF"
                      ? "bg-primary/10 text-primary"
                      : cliente.client_type === "SX"
                      ? "bg-accent/10 text-accent"
                      : "bg-secondary"
                  }
                >
                  {cliente.client_type}
                </Badge>
              </div>
            </div>
            <div className="space-y-1 text-sm">
              {cliente.dui && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">DUI:</span>
                  <span className="font-medium">{cliente.dui}</span>
                </div>
              )}
              {cliente.nit && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">NIT:</span>
                  <span className="font-medium">{cliente.nit}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground">Teléfono:</span>
                <span className="font-medium">{cliente.phone || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email:</span>
                <span className="font-medium truncate">{cliente.email || "-"}</span>
              </div>
            </div>
          </div>
        ))}
        {!loading && filteredClients.length === 0 && !error && (
          <div className="text-sm text-muted-foreground">
            No hay clientes registrados.
          </div>
        )}
      </div>

      {/* Desktop view - Table */}
      <div className="hidden md:block rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-sm font-medium">Nombre / Razón Social</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Tipo</th>
                <th className="px-4 py-3 text-left text-sm font-medium">DUI / NIT</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Teléfono</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Correo</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td className="px-4 py-3 text-sm" colSpan={5}>
                    Cargando clientes...
                  </td>
                </tr>
              )}
              {error && !loading && (
                <tr>
                  <td
                    className="px-4 py-3 text-sm text-destructive"
                    colSpan={5}
                  >
                    {error}
                  </td>
                </tr>
              )}
              {!loading &&
                filteredClients.map((cliente) => (
                <tr
                  key={cliente.id}
                  onClick={() => {
                    if (modoEdicion) {
                      setClienteSeleccionado(cliente);
                      setShowEditarModal(true);
                    }
                  }}
                  className={`border-b border-border hover:bg-muted/30 transition-colors ${
                    modoEdicion ? "cursor-pointer" : ""
                  }`}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium">{cliente.full_name}</p>
                      {cliente.company_name && (
                        <p className="text-sm text-muted-foreground">
                          {cliente.company_name}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant="outline"
                      className={
                        cliente.client_type === "CCF"
                          ? "bg-primary/10 text-primary"
                          : cliente.client_type === "SX"
                          ? "bg-accent/10 text-accent"
                          : "bg-secondary"
                      }
                    >
                      {cliente.client_type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono">
                    {cliente.dui || cliente.nit || "-"}
                  </td>
                  <td className="px-4 py-3 text-sm">{cliente.phone || "-"}</td>
                  <td className="px-4 py-3 text-sm">{cliente.email || "-"}</td>
                </tr>
                ))}
              {!loading && filteredClients.length === 0 && !error && (
                <tr>
                  <td
                    className="px-4 py-3 text-sm text-muted-foreground"
                    colSpan={5}
                  >
                    No hay clientes registrados.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <NuevoClienteModal
        open={showNuevoModal}
        onOpenChange={setShowNuevoModal}
        onSubmit={async (payload) => {
          await handleCreateClient(payload);
          setShowNuevoModal(false);
        }}
      />
      <EditarClienteModal
        open={showEditarModal}
        onOpenChange={setShowEditarModal}
        cliente={clienteSeleccionado}
        onSubmit={async (payload) => {
          if (!clienteSeleccionado) return;
          await handleUpdateClient(clienteSeleccionado.id, payload);
          setShowEditarModal(false);
        }}
        onDelete={async () => {
          if (!clienteSeleccionado) return;
          await handleDeleteClient(clienteSeleccionado.id);
          setShowEditarModal(false);
        }}
      />
    </div>
  );
}
