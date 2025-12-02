import { useEffect, useMemo, useState } from "react";
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
import { NuevoGastoModal } from "@/components/modals/NuevoGastoModal";
import { VerGastoModal } from "@/components/modals/VerGastoModal";
import { api } from "@/lib/api";
import { Expense, ExpensePayload } from "@/types/expense";

export default function Gastos() {
  const [filter, setFilter] = useState("all");
  const [showNuevoModal, setShowNuevoModal] = useState(false);
  const [showVerModal, setShowVerModal] = useState(false);
  const [gastoSeleccionado, setGastoSeleccionado] = useState<Expense | null>(
    null,
  );
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");

  const fetchExpenses = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<Expense[]>("/expenses/");
      setExpenses(response.data);
    } catch (err) {
      console.error("Error al cargar gastos", err);
      setError("No se pudieron cargar los gastos");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateExpense = async (payload: ExpensePayload) => {
    await api.post("/expenses/", payload);
    await fetchExpenses();
  };

  useEffect(() => {
    fetchExpenses();
  }, []);

  const filteredExpenses = useMemo(() => {
    const term = searchTerm.toLowerCase();
    return expenses.filter((expense) => {
      const matchesSearch =
        expense.name.toLowerCase().includes(term) ||
        expense.provider.toLowerCase().includes(term);

      if (filter === "all") return matchesSearch;

      const expenseDate = new Date(expense.date);
      const today = new Date();

      if (filter === "today") {
        return (
          matchesSearch &&
          expenseDate.toDateString() === today.toDateString()
        );
      }

      if (filter === "week") {
        const diffDays =
          (today.getTime() - expenseDate.getTime()) / (1000 * 60 * 60 * 24);
        return matchesSearch && diffDays <= 7;
      }

      if (filter === "month") {
        return (
          matchesSearch &&
          expenseDate.getMonth() === today.getMonth() &&
          expenseDate.getFullYear() === today.getFullYear()
        );
      }

      return matchesSearch;
    });
  }, [expenses, filter, searchTerm]);

  const totalExpensesAmount = useMemo(() => {
    return filteredExpenses.reduce((sum, expense) => {
      const total = Number(expense.total) || 0;
      return sum + total;
    }, 0);
  }, [filteredExpenses]);

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
          <Input
            placeholder="Buscar por nombre, proveedor..."
            className="w-full"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
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
      <div className="flex justify-end text-sm md:text-base font-semibold text-muted-foreground">
        <span>Total de gastos (según filtros): ${totalExpensesAmount.toFixed(2)}</span>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {loading && (
          <div className="p-4 text-sm text-muted-foreground">
            Cargando gastos...
          </div>
        )}
        {error && !loading && (
          <div className="p-4 text-sm text-destructive">{error}</div>
        )}
        {!loading && filteredExpenses.length === 0 && !error && (
          <div className="p-4 text-sm text-muted-foreground">
            No hay gastos registrados.
          </div>
        )}
        {!loading &&
          filteredExpenses.map((gasto) => (
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
                  <p className="font-semibold text-base truncate">{gasto.name}</p>
                  <p className="text-sm text-muted-foreground truncate">
                    {gasto.provider}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">{gasto.date}</p>
                </div>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-border">
                <span className="text-muted-foreground text-sm">Total:</span>
                <span className="font-bold text-lg">
                  ${Number(gasto.total).toFixed(2)}
                </span>
              </div>
            </div>
          ))}
      </div>

      {/* Desktop view - Table */}
      <div className="hidden md:block rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          {loading && (
            <div className="p-4 text-sm text-muted-foreground">Cargando gastos...</div>
          )}
          {error && !loading && (
            <div className="p-4 text-sm text-destructive">{error}</div>
          )}
          {!loading && (
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
                {filteredExpenses.map((gasto) => (
                  <tr
                    key={gasto.id}
                    onClick={() => {
                      setGastoSeleccionado(gasto);
                      setShowVerModal(true);
                    }}
                    className="border-b border-border hover:bg-muted/30 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-3 font-medium">{gasto.name}</td>
                    <td className="px-4 py-3 text-sm">{gasto.provider}</td>
                    <td className="px-4 py-3 text-sm">{gasto.date}</td>
                    <td className="px-4 py-3 text-right font-semibold">
                      ${Number(gasto.total).toFixed(2)}
                    </td>
                  </tr>
                ))}
                {filteredExpenses.length === 0 && (
                  <tr>
                    <td
                      className="px-4 py-3 text-sm text-muted-foreground"
                      colSpan={4}
                    >
                      No hay gastos registrados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <NuevoGastoModal
        open={showNuevoModal}
        onOpenChange={setShowNuevoModal}
        onSubmit={async (payload) => {
          await handleCreateExpense(payload);
          setShowNuevoModal(false);
        }}
      />
      <VerGastoModal
        open={showVerModal}
        onOpenChange={setShowVerModal}
        gasto={gastoSeleccionado}
      />
    </div>
  );
}
