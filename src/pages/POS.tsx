import { useState } from "react";
import { Plus, FileText, Download, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function POS() {
  const [filter, setFilter] = useState("all");

  const ventas = [
    {
      id: 1,
      numero: "DTE-001234",
      fecha: "2024-01-15",
      cliente: "Juan Pérez",
      tipo: "CF",
      metodoPago: "Efectivo",
      estadoDTE: "Aprobado",
      total: 150.0,
    },
    {
      id: 2,
      numero: "DTE-001235",
      fecha: "2024-01-15",
      cliente: "Empresa ABC S.A.",
      tipo: "CCF",
      metodoPago: "Transferencia",
      estadoDTE: "Aprobado",
      total: 450.0,
    },
    {
      id: 3,
      numero: "DTE-001236",
      fecha: "2024-01-14",
      cliente: "María González",
      tipo: "CF",
      metodoPago: "Tarjeta",
      estadoDTE: "Pendiente",
      total: 280.0,
    },
  ];

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      <div className="flex justify-end">
        <Button className="bg-primary hover:bg-primary/90 w-full md:w-auto">
          <Plus className="h-4 w-4 mr-2" />
          <span className="md:hidden">Nueva</span>
          <span className="hidden md:inline">Nueva Factura</span>
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 md:gap-4">
        <div className="flex-1">
          <Input placeholder="Buscar por número, cliente..." className="w-full" />
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
        {ventas.map((venta) => (
          <div
            key={venta.id}
            className="rounded-lg border border-border bg-card p-4 shadow-elegant"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-semibold text-lg">{venta.numero}</p>
                <p className="text-sm text-muted-foreground">{venta.fecha}</p>
              </div>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${
                  venta.estadoDTE === "Aprobado"
                    ? "bg-success/10 text-success"
                    : "bg-warning/10 text-warning"
                }`}
              >
                {venta.estadoDTE}
              </span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Cliente:</span>
                <span className="font-medium">{venta.cliente}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Tipo:</span>
                <span className="font-medium">{venta.tipo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Pago:</span>
                <span className="font-medium">{venta.metodoPago}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-border">
                <span className="text-muted-foreground">Total:</span>
                <span className="font-bold text-lg">${venta.total.toFixed(2)}</span>
              </div>
            </div>
            <Button variant="outline" size="sm" className="w-full mt-3">
              <FileText className="h-3 w-3 mr-2" />
              Ver Detalles
            </Button>
          </div>
        ))}
      </div>

      {/* Desktop view - Table */}
      <div className="hidden md:block rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr className="border-b border-border">
                <th className="px-4 py-3 text-left text-sm font-medium">Nº Factura</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Fecha</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Cliente</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Tipo</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Método Pago</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Estado DTE</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Total</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {ventas.map((venta) => (
                <tr key={venta.id} className="border-b border-border hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-medium">{venta.numero}</td>
                  <td className="px-4 py-3 text-sm">{venta.fecha}</td>
                  <td className="px-4 py-3 text-sm">{venta.cliente}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-primary/10 text-primary font-medium">
                      {venta.tipo}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">{venta.metodoPago}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        venta.estadoDTE === "Aprobado"
                          ? "bg-success/10 text-success"
                          : "bg-warning/10 text-warning"
                      }`}
                    >
                      {venta.estadoDTE}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">${venta.total.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" size="sm">
                      <FileText className="h-4 w-4" />
                      <span className="sr-only">Ver detalles</span>
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
