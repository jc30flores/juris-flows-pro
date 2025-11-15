import { useState } from "react";
import { Plus, Edit, Briefcase } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function Servicios() {
  const [modoEdicion, setModoEdicion] = useState(false);

  const servicios = [
    {
      id: 1,
      codigo: "SRV-001",
      nombre: "Compra Venta de Vehículos",
      categoria: "Compra Venta",
      precioBase: 150.0,
      imponible: true,
      activo: true,
    },
    {
      id: 2,
      codigo: "SRV-002",
      nombre: "Escritura Pública: Compra Venta de Inmuebles",
      categoria: "Escrituras Públicas",
      precioBase: 450.0,
      imponible: true,
      activo: true,
    },
    {
      id: 3,
      codigo: "SRV-003",
      nombre: "Escritura Pública: Promesa de Venta",
      categoria: "Escrituras Públicas",
      precioBase: 300.0,
      imponible: true,
      activo: true,
    },
    {
      id: 4,
      codigo: "SRV-004",
      nombre: "Compra Venta de Arma de Fuego",
      categoria: "Compra Venta",
      precioBase: 120.0,
      imponible: true,
      activo: true,
    },
    {
      id: 5,
      codigo: "SRV-005",
      nombre: "Autenticación de Documentos",
      categoria: "Autenticaciones",
      precioBase: 50.0,
      imponible: true,
      activo: true,
    },
    {
      id: 6,
      codigo: "SRV-006",
      nombre: "Certificación de Documentos",
      categoria: "Certificaciones",
      precioBase: 40.0,
      imponible: true,
      activo: true,
    },
    {
      id: 7,
      codigo: "SRV-007",
      nombre: "Escritura de Poder Especial",
      categoria: "Poderes",
      precioBase: 200.0,
      imponible: true,
      activo: true,
    },
    {
      id: 8,
      codigo: "SRV-008",
      nombre: "Documento Autenticado de Arrendamiento",
      categoria: "Arrendamientos",
      precioBase: 180.0,
      imponible: true,
      activo: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Catálogo de Servicios</h2>
          <p className="text-muted-foreground mt-1">
            Servicios jurídicos y notariales disponibles
          </p>
        </div>
        <div className="flex items-center gap-4">
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
            <Button className="bg-primary hover:bg-primary/90">
              <Plus className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline">Nuevo Servicio</span>
              <span className="sm:hidden">Nuevo</span>
            </Button>
          )}
        </div>
      </div>

      {/* Tabla de Servicios */}
      <div className="rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-sm font-medium">Código</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Servicio</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Categoría</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Precio Base</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Imponible</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Estado</th>
                {modoEdicion && (
                  <th className="px-4 py-3 text-right text-sm font-medium">Acciones</th>
                )}
              </tr>
            </thead>
            <tbody>
              {servicios.map((servicio) => (
                <tr
                  key={servicio.id}
                  className="border-b border-border hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-sm">{servicio.codigo}</td>
                  <td className="px-4 py-3 font-medium">{servicio.nombre}</td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {servicio.categoria}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-accent">
                    ${servicio.precioBase.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {servicio.imponible && (
                      <Badge variant="outline" className="text-xs">
                        Sí
                      </Badge>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Badge
                      variant={servicio.activo ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {servicio.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  {modoEdicion && (
                    <td className="px-4 py-3 text-right">
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4 mr-2" />
                        Editar
                      </Button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
