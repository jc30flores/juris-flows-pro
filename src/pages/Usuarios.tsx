import { useState } from "react";
import { Plus, UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NuevoUsuarioModal } from "@/components/modals/NuevoUsuarioModal";

export default function Usuarios() {
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const usuarios = [
    {
      id: 1,
      nombre: "Admin Usuario",
      email: "admin@cuska.local",
      rol: "ADMIN",
      activo: true,
    },
    {
      id: 2,
      nombre: "María Colaboradora",
      email: "mcolaboradora@cuska.local",
      rol: "COLABORADOR",
      activo: true,
    },
    {
      id: 3,
      nombre: "Juan Contador",
      email: "jcontador@cuska.local",
      rol: "CONTADOR",
      activo: true,
    },
  ];

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
        <div className="flex-1">
          <Input placeholder="Buscar por nombre o email..." className="w-full" />
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {usuarios.map((usuario) => (
          <div
            key={usuario.id}
            className="rounded-lg border border-border bg-card p-4 shadow-elegant hover:shadow-elegant-lg transition-smooth"
          >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <UserCog className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-base truncate">{usuario.nombre}</p>
                  <Badge variant="outline" className={getRolBadgeColor(usuario.rol)}>
                    {usuario.rol}
                  </Badge>
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
                <th className="px-4 py-3 text-left text-sm font-medium">Rol</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => (
                <tr
                  key={usuario.id}
                  className="border-b border-border hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 font-medium">{usuario.nombre}</td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className={getRolBadgeColor(usuario.rol)}>
                      {usuario.rol}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm">
                      Editar
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
      />
    </div>
  );
}
