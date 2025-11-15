import { useState } from "react";
import { Plus, Search, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function Clientes() {
  const clientes = [
    {
      id: 1,
      nombre: "Juan Alberto Pérez",
      tipoFiscal: "CF",
      dui: "01234567-8",
      telefono: "7890-1234",
      correo: "juan@email.com",
    },
    {
      id: 2,
      nombre: "Empresa ABC S.A. de C.V.",
      nombreComercial: "ABC Corp",
      tipoFiscal: "CCF",
      nit: "0614-123456-001-2",
      nrc: "123456-7",
      telefono: "2222-3333",
      correo: "info@abc.com",
    },
    {
      id: 3,
      nombre: "María González",
      tipoFiscal: "SX",
      telefono: "7555-4321",
      correo: "maria@email.com",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Clientes</h2>
          <p className="text-muted-foreground mt-1">
            Gestión de clientes y contribuyentes
          </p>
        </div>
        <Button className="bg-primary hover:bg-primary/90">
          <Plus className="h-4 w-4 mr-2" />
          <span className="hidden sm:inline">Nuevo Cliente</span>
          <span className="sm:hidden">Nuevo</span>
        </Button>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Buscar por nombre, DUI, NIT..." className="pl-9" />
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {clientes.map((cliente) => (
          <div
            key={cliente.id}
            className="rounded-lg border border-border bg-card p-4 shadow-elegant hover:shadow-elegant-lg transition-smooth cursor-pointer"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <p className="font-semibold text-lg mb-1">{cliente.nombre}</p>
                {cliente.nombreComercial && (
                  <p className="text-sm text-muted-foreground mb-2">
                    {cliente.nombreComercial}
                  </p>
                )}
                <Badge
                  variant="outline"
                  className={
                    cliente.tipoFiscal === "CCF"
                      ? "bg-primary/10 text-primary"
                      : cliente.tipoFiscal === "SX"
                      ? "bg-accent/10 text-accent"
                      : "bg-secondary"
                  }
                >
                  {cliente.tipoFiscal}
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
                <span className="font-medium">{cliente.telefono}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email:</span>
                <span className="font-medium truncate">{cliente.correo}</span>
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
                <th className="px-4 py-3 text-left text-sm font-medium">Nombre / Razón Social</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Tipo</th>
                <th className="px-4 py-3 text-left text-sm font-medium">DUI / NIT</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Teléfono</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Correo</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente) => (
                <tr
                  key={cliente.id}
                  className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium">{cliente.nombre}</p>
                      {cliente.nombreComercial && (
                        <p className="text-sm text-muted-foreground">
                          {cliente.nombreComercial}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge
                      variant="outline"
                      className={
                        cliente.tipoFiscal === "CCF"
                          ? "bg-primary/10 text-primary"
                          : cliente.tipoFiscal === "SX"
                          ? "bg-accent/10 text-accent"
                          : "bg-secondary"
                      }
                    >
                      {cliente.tipoFiscal}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono">
                    {cliente.dui || cliente.nit || "-"}
                  </td>
                  <td className="px-4 py-3 text-sm">{cliente.telefono}</td>
                  <td className="px-4 py-3 text-sm">{cliente.correo}</td>
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
    </div>
  );
}
