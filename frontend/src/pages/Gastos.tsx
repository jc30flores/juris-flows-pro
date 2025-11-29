import { useState } from "react";
import { Plus, Download, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { NuevoGastoModal } from "@/components/modals/NuevoGastoModal";
import { VerGastoModal } from "@/components/modals/VerGastoModal";

export default function Gastos() {
  const [filter, setFilter] = useState("all");
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const [showVerModal, setShowVerModal] = useState(false);
  const [gastoSeleccionado, setGastoSeleccionado] = useState<any>(null);

  const gastos = [
    {
      id: 1,
      nombre: "Papelería y Suministros",
      proveedor: "Librería Central",
      fecha: "2024-01-15",
      total: 85.50,
    },
    {
      id: 2,
      nombre: "Servicios de Internet",
      proveedor: "Telecom SV",
      fecha: "2024-01-14",
      total: 45.00,
    },
    {
      id: 3,
      nombre: "Mantenimiento de Oficina",
      proveedor: "Servicios Generales",
      fecha: "2024-01-13",
      total: 120.00,
    },
  ];

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      {/* Título móvil */}
      <h2 className="text-lg font-semibold md:hidden">Gastos</h2>
      <div className="flex justify-end">
        <Button 
          className="bg-primary hover:bg-primary/90 w-full md:w-auto"
          onClick={() => setShowNuevoModal(true)}
        >
          <Plus className="h-4 w-4 mr-2" />
          <span className="md:hidden">Nuevo</span>
          <span className="hidden md:inline">Nuevo Gasto</span>
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 md:gap-4">
        <div className="flex-1">
          <Input placeholder="Buscar por nombre, proveedor..." className="w-full" />
        </div>
        <div className="flex gap-2">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-full sm:w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Filtrar por..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="today">Hoy</SelectItem>
              <SelectItem value="week">Esta Semana</SelectItem>
              <SelectItem value="month">Este Mes</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="flex-shrink-0">
            <Download className="h-4 w-4 md:mr-2" />
            <span className="hidden md:inline">Exportar</span>
          </Button>
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {gastos.map((gasto) => (
          <div
            key={gasto.id}
            onClick={() => {
              setGastoSeleccionado(gasto);
              setShowVerModal(true);
            }}
            className="rounded-lg border border-border bg-card p-4 shadow-elegant cursor-pointer hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-base truncate">{gasto.nombre}</p>
                <p className="text-sm text-muted-foreground truncate">{gasto.proveedor}</p>
                <p className="text-xs text-muted-foreground mt-1">{gasto.fecha}</p>
              </div>
            </div>
            <div className="flex items-center justify-between pt-3 border-t border-border">
              <span className="text-muted-foreground text-sm">Total:</span>
              <span className="font-bold text-lg">${gasto.total.toFixed(2)}</span>
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
                <th className="px-4 py-3 text-left text-sm font-medium">Proveedor</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Fecha</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Total</th>
              </tr>
            </thead>
            <tbody>
              {gastos.map((gasto) => (
                <tr 
                  key={gasto.id} 
                  onClick={() => {
                    setGastoSeleccionado(gasto);
                    setShowVerModal(true);
                  }}
                  className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium">{gasto.nombre}</td>
                  <td className="px-4 py-3 text-sm">{gasto.proveedor}</td>
                  <td className="px-4 py-3 text-sm">{gasto.fecha}</td>
                  <td className="px-4 py-3 text-right font-semibold">${gasto.total.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <NuevoGastoModal
        open={showNuevoModal}
        onOpenChange={setShowNuevoModal}
      />
      <VerGastoModal
        open={showVerModal}
        onOpenChange={setShowVerModal}
        gasto={gastoSeleccionado}
      />
    </div>
  );
}
