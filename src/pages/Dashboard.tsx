import { DollarSign, Receipt, Users, TrendingUp } from "lucide-react";
import { StatCard } from "@/components/StatCard";

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground mt-1">
          Resumen de operaciones y métricas clave
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Ventas del Día"
          value="$2,845.00"
          icon={DollarSign}
          trend={{ value: "12% vs ayer", positive: true }}
        />
        <StatCard
          title="Facturas Emitidas"
          value="24"
          icon={Receipt}
          trend={{ value: "8 pendientes DTE", positive: false }}
        />
        <StatCard
          title="Clientes Activos"
          value="186"
          icon={Users}
          trend={{ value: "3 nuevos hoy", positive: true }}
        />
        <StatCard
          title="Ingresos del Mes"
          value="$48,392.00"
          icon={TrendingUp}
          trend={{ value: "18% vs mes anterior", positive: true }}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-6 shadow-elegant">
          <h3 className="text-lg font-semibold mb-4">Ventas Recientes</h3>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                <div>
                  <p className="font-medium">Factura #{1000 + i}</p>
                  <p className="text-sm text-muted-foreground">Cliente Example {i}</p>
                </div>
                <div className="text-right">
                  <p className="font-semibold">${(Math.random() * 500 + 100).toFixed(2)}</p>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-success/10 text-success">
                    Aprobado
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-6 shadow-elegant">
          <h3 className="text-lg font-semibold mb-4">Servicios Más Vendidos</h3>
          <div className="space-y-3">
            {[
              "Compra Venta de Vehículos",
              "Escritura Pública: Compra Venta",
              "Autenticación de Documentos",
              "Poder Especial"
            ].map((service, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <p className="text-sm">{service}</p>
                <span className="text-sm font-medium text-accent">
                  {Math.floor(Math.random() * 20 + 5)} ventas
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
