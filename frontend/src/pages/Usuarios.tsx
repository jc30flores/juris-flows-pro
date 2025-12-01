import { useEffect, useMemo, useState } from "react";
import { Plus, Search, UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NuevoUsuarioModal } from "@/components/modals/NuevoUsuarioModal";
import { EditarUsuarioModal } from "@/components/modals/EditarUsuarioModal";
import { api } from "@/lib/api";
import { StaffUser, StaffUserPayload } from "@/types/staffUser";

export default function Usuarios() {
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const [showEditarModal, setShowEditarModal] = useState(false);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState<
    StaffUser | null
  >(null);
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const fetchUsers = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<StaffUser[]>("/staff-users/");
      setUsers(response.data);
    } catch (err) {
      console.error("Error al cargar usuarios", err);
      setError("No se pudieron cargar los usuarios");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (payload: StaffUserPayload) => {
    await api.post("/staff-users/", payload);
    await fetchUsers();
  };

  const handleUpdateUser = async (
    id: number,
    payload: Partial<StaffUserPayload>,
  ) => {
    await api.patch(`/staff-users/${id}/`, payload);
    await fetchUsers();
  };

  const handleDeleteUser = async (id: number) => {
    await api.delete(`/staff-users/${id}/`);
    setUsers((prev) => prev.filter((user) => user.id !== id));
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    const query = search.toLowerCase();
    return users.filter((user) => {
      return (
        user.full_name.toLowerCase().includes(query) ||
        user.username.toLowerCase().includes(query) ||
        user.role.toLowerCase().includes(query)
      );
    });
  }, [users, search]);

  const getRolBadgeColor = (rol: string) => {
    switch (rol) {
      case "ADMIN":
        return "bg-primary/10 text-primary";
      case "COLABORADOR":
        return "bg-accent/10 text-accent";
      case "CONTADOR":
        return "bg-warning/10 text-warning";
      default:
        return "bg-secondary";
    }
  };

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      {/* Título móvil */}
      <h2 className="text-lg font-semibold md:hidden">Usuarios</h2>
      <div className="flex justify-end">
        <Button
          className="bg-primary hover:bg-primary/90 w-full md:w-auto"
          onClick={() => setShowNuevoModal(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          <span className="md:hidden">Nuevo</span>
          <span className="hidden md:inline">Nuevo Usuario</span>
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre, usuario o rol..."
            className="pl-9"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {loading && (
          <div className="text-sm text-muted-foreground">Cargando usuarios...</div>
        )}
        {error && !loading && (
          <div className="text-sm text-destructive">{error}</div>
        )}
        {!loading && !error && filteredUsers.length === 0 && (
          <div className="text-sm text-muted-foreground">No hay usuarios.</div>
        )}
        {filteredUsers.map((usuario) => (
          <div
            key={usuario.id}
            className="rounded-lg border border-border bg-card p-4 shadow-elegant hover:shadow-elegant-lg transition-smooth"
          >
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                <UserCog className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-base truncate">{usuario.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">{usuario.username}</p>
                <Badge variant="outline" className={getRolBadgeColor(usuario.role)}>
                  {usuario.role}
                </Badge>
              </div>
              <div className="flex flex-col gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setUsuarioSeleccionado(usuario);
                    setShowEditarModal(true);
                  }}
                >
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => handleDeleteUser(usuario.id)}
                >
                  Eliminar
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Desktop view - Table */}
      <div className="hidden md:block rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-sm font-medium">Nombre</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Usuario</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Rol</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td className="px-4 py-3 text-sm text-muted-foreground" colSpan={4}>
                    Cargando usuarios...
                  </td>
                </tr>
              )}
              {error && !loading && (
                <tr>
                  <td className="px-4 py-3 text-sm text-destructive" colSpan={4}>
                    {error}
                  </td>
                </tr>
              )}
              {!loading && !error && filteredUsers.length === 0 && (
                <tr>
                  <td className="px-4 py-3 text-sm text-muted-foreground" colSpan={4}>
                    No hay usuarios.
                  </td>
                </tr>
              )}
              {!loading && !error &&
                filteredUsers.map((usuario) => (
                  <tr
                    key={usuario.id}
                    className="border-b border-border hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium">{usuario.full_name}</td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{usuario.username}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={getRolBadgeColor(usuario.role)}
                      >
                        {usuario.role}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setUsuarioSeleccionado(usuario);
                          setShowEditarModal(true);
                        }}
                      >
                        Editar
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => handleDeleteUser(usuario.id)}
                      >
                        Eliminar
                      </Button>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      <NuevoUsuarioModal
        open={showNuevoModal}
        onOpenChange={setShowNuevoModal}
        onSubmit={handleCreateUser}
      />

      <EditarUsuarioModal
        open={showEditarModal}
        onOpenChange={setShowEditarModal}
        usuario={usuarioSeleccionado}
        onSubmit={async (payload) => {
          if (!usuarioSeleccionado) return;
          await handleUpdateUser(usuarioSeleccionado.id, payload);
        }}
        onDelete={async () => {
          if (!usuarioSeleccionado) return;
          await handleDeleteUser(usuarioSeleccionado.id);
        }}
      />
    </div>
  );
}
