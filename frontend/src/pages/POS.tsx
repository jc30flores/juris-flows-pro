import { useEffect, useMemo, useState } from "react";
import { Plus, Download, Filter, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { NuevaFacturaModal } from "@/components/modals/NuevaFacturaModal";
import { ServiceSelectorModal } from "@/components/modals/ServiceSelectorModal";
import { API_BASE_URL, api } from "@/lib/api";
import { Client } from "@/types/client";
import { Invoice, InvoicePayload, SelectedServicePayload } from "@/types/invoice";
import { Service } from "@/types/service";
import { toast } from "@/hooks/use-toast";

const getDteBadgeStyle = (status: string | undefined) => {
  const normalized = status?.toUpperCase();
  if (normalized === "ACEPTADO" || status === "Aprobado") {
    return "bg-success/10 text-success";
  }
  if (normalized === "RECHAZADO" || status === "Rechazado" || normalized === "ERROR") {
    return "bg-destructive/10 text-destructive";
  }
  return "bg-warning/10 text-warning";
};

const getDteDisplayStatus = (status: string | undefined) => {
  const normalized = status?.toUpperCase();
  if (normalized === "ACEPTADO") return "ACEPTADO";
  if (normalized === "RECHAZADO") return "RECHAZADO";
  if (normalized === "PENDIENTE") return "Pendiente";
  return status || "";
};

const isInvoiceInCurrentMonth = (dateValue: string | Date): boolean => {
  if (!dateValue) return false;
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth();

  const d = typeof dateValue === "string" ? new Date(dateValue) : dateValue;
  if (Number.isNaN(d.getTime())) return false;

  return d.getFullYear() === currentYear && d.getMonth() === currentMonth;
};

export default function POS() {
  const now = new Date();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [showNuevaFacturaModal, setShowNuevaFacturaModal] = useState(false);
  const [showServiceSelectorModal, setShowServiceSelectorModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportDteType, setExportDteType] = useState<
    "consumidores" | "contribuyentes"
  >("consumidores");
  const [exportMonth, setExportMonth] = useState(String(now.getMonth() + 1));
  const [exportYear] = useState(now.getFullYear());
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedServices, setSelectedServices] = useState<SelectedServicePayload[]>([]);

  const fetchInitialData = async () => {
    setLoading(true);
    setError("");
    try {
      const [invoiceResponse, clientResponse, serviceResponse] =
        await Promise.all([
          api.get<Invoice[]>("/invoices/"),
          api.get<Client[]>("/clients/"),
          api.get<Service[]>("/services/"),
        ]);

      setInvoices(invoiceResponse.data);
      setClients(clientResponse.data);
      setServices(serviceResponse.data);
    } catch (err) {
      console.error("Error al cargar facturas", err);
      setError("No se pudieron cargar las facturas");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const handleSaveInvoice = async (payload: InvoicePayload) => {
    try {
      if (selectedInvoice) {
        await api.patch(`/invoices/${selectedInvoice.id}/`, payload);
        toast({
          title: "Factura actualizada",
          description: "Los cambios se guardaron correctamente.",
        });
      } else {
        const response = await api.post<Invoice>("/invoices/", payload);
        const invoice = response.data;

        const normalizedStatus = invoice.dte_status?.toUpperCase();
        if (normalizedStatus === "ACEPTADO" || invoice.dte_status === "Aprobado") {
          toast({
            title: "Factura creada",
            description:
              invoice.dte_message || "Factura creada y DTE aceptado por Hacienda.",
          });
        } else if (
          normalizedStatus === "RECHAZADO" ||
          invoice.dte_status === "Rechazado" ||
          normalizedStatus === "ERROR"
        ) {
          toast({
            title: "DTE rechazado",
            description:
              invoice.dte_message ||
              "Factura creada, pero el DTE fue rechazado por Hacienda. Revisa los datos.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "Factura creada",
            description: "DTE pendiente de envío o procesamiento.",
          });
        }
      }

      await fetchInitialData();
      setSelectedInvoice(null);
      setMode("create");
      setSelectedServices([]);
      setShowNuevaFacturaModal(false);
      setShowServiceSelectorModal(false);
    } catch (err) {
      console.error("Error al guardar factura", err);
      toast({
        title: "No se pudo guardar la factura",
        description: "Revisa los datos e intenta nuevamente.",
        variant: "destructive",
      });
    }
  };

  const handleDeleteInvoice = async (invoiceId: number) => {
    try {
      await api.delete(`/invoices/${invoiceId}/`);
      setInvoices((prev) => prev.filter((invoice) => invoice.id !== invoiceId));
      toast({
        title: "Factura eliminada",
        description: "La factura se ha eliminado correctamente",
      });
    } catch (err) {
      console.error("Error al eliminar factura", err);
      toast({
        title: "No se pudo eliminar la factura",
        description: "Intenta nuevamente.",
        variant: "destructive",
      });
    }
  };

  const clientLookup = useMemo(() => {
    return clients.reduce<Record<number, string>>((acc, client) => {
      acc[client.id] = client.company_name || client.full_name;
      return acc;
    }, {});
  }, [clients]);

  const filteredInvoices = useMemo(() => {
    const today = new Date().toISOString().split("T")[0];
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());

    return invoices.filter((invoice) => {
      const matchesSearch = `${invoice.number} ${clientLookup[invoice.client] || ""}`
        .toLowerCase()
        .includes(search.toLowerCase());

      if (!matchesSearch) return false;

      const invoiceDate = new Date(invoice.date);

      if (filter === "today") {
        return invoice.date === today;
      }

      if (filter === "week" || filter === "this-week") {
        return invoiceDate >= startOfWeek;
      }

      if (filter === "month" || filter === "this-month") {
        return isInvoiceInCurrentMonth(invoice.date);
      }

      return true;
    });
  }, [clientLookup, filter, invoices, search]);

  const totalInvoicesAmount = useMemo(() => {
    return filteredInvoices.reduce((sum, invoice) => {
      const total = Number(invoice.total) || 0;
      return sum + total;
    }, 0);
  }, [filteredInvoices]);

  const handleOpenCreate = () => {
    setMode("create");
    setSelectedInvoice(null);
    setSelectedServices([]);
    setShowServiceSelectorModal(true);
    setShowNuevaFacturaModal(false);
  };

  const handleOpenEdit = (invoice: Invoice) => {
    setMode("edit");
    setSelectedInvoice(invoice);
    const items = invoice.items || [];
    const mappedServices = items.map((item) => {
      const service = services.find((s) => s.id === item.service);
      const price = Number(item.unit_price || service?.base_price || 0);
      const quantity = item.quantity || 1;
      return {
        service_id: item.service,
        name: service?.name || `Servicio ${item.service}`,
        price,
        quantity,
        subtotal: Number((price * quantity).toFixed(2)),
      } as SelectedServicePayload;
    });

    setSelectedServices(mappedServices);
    setShowServiceSelectorModal(false);
    setShowNuevaFacturaModal(true);
  };

  const handleConfirmServices = (servicesSelected: SelectedServicePayload[]) => {
    setSelectedServices(servicesSelected);
    setShowServiceSelectorModal(false);
    setShowNuevaFacturaModal(true);
  };

  const handleCancelSelection = () => {
    setSelectedServices([]);
    setShowServiceSelectorModal(false);
    setShowNuevaFacturaModal(false);
    setSelectedInvoice(null);
    setMode("create");
  };

  const handleOpenExportModal = () => setShowExportModal(true);

  const handleDownload = () => {
    const params = new URLSearchParams({
      dte_type: exportDteType,
      month: exportMonth,
      year: String(exportYear),
    });

    const url = `${API_BASE_URL}/api/invoices/export/?${params.toString()}`;

    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setShowExportModal(false);
  };

  return (
    <div className="space-y-4 md:space-y-6 overflow-x-hidden">
      {/* Título móvil */}
      <h2 className="text-lg font-semibold md:hidden">Facturador</h2>
      <div className="flex justify-end">
        <Button
          className="bg-primary hover:bg-primary/90 w-full md:w-auto"
          onClick={handleOpenCreate}
        >
          <Plus className="h-4 w-4 mr-2" />
          <span className="md:hidden">Nueva</span>
          <span className="hidden md:inline">Nueva Factura</span>
        </Button>
      </div>

      <div className="flex flex-col gap-2 md:gap-3">
        <div className="flex flex-col sm:flex-row gap-3 md:gap-4">
          <div className="flex-1">
            <Input
              placeholder="Buscar por número, cliente..."
              className="w-full"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
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
            <Button
              variant="outline"
              className="flex-shrink-0"
              onClick={handleOpenExportModal}
            >
              <Download className="h-4 w-4 md:mr-2" />
              <span className="hidden md:inline">Exportar</span>
            </Button>
          </div>
        </div>
        <div className="flex justify-end text-sm md:text-base font-semibold text-muted-foreground">
          <span>
            Total facturado (según filtros): ${totalInvoicesAmount.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Mobile view - Cards */}
      <div className="grid gap-4 md:hidden">
        {loading && (
          <div className="p-4 text-sm text-muted-foreground">Cargando facturas...</div>
        )}
        {!loading && error && (
          <div className="p-4 text-sm text-destructive">{error}</div>
        )}
        {!loading && !error &&
          filteredInvoices.map((venta) => (
            <div
              key={venta.id}
              className="rounded-lg border border-border bg-card p-4 shadow-elegant"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-lg">{venta.number}</p>
                  <p className="text-sm text-muted-foreground">
                    {venta.date_display || venta.date}
                  </p>
                </div>
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${getDteBadgeStyle(
                    venta.dte_status,
                  )}`}
                >
                  {getDteDisplayStatus(venta.dte_status)}
                </span>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Cliente:</span>
                  <span className="font-medium">
                    {clientLookup[venta.client] || "Sin cliente"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tipo:</span>
                  <span className="font-medium">{venta.doc_type}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Pago:</span>
                  <span className="font-medium">{venta.payment_method}</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-border">
                  <span className="text-muted-foreground">Total:</span>
                  <span className="font-bold text-lg">
                    ${Number(venta.total).toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => handleOpenEdit(venta)}
                >
                  <Pencil className="h-3 w-3 mr-2" />
                  Editar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1"
                  onClick={() => handleDeleteInvoice(venta.id)}
                >
                  <Trash2 className="h-3 w-3 mr-2 text-destructive" />
                  Eliminar
                </Button>
              </div>
            </div>
          ))}
        {!loading && !error && filteredInvoices.length === 0 && (
          <div className="p-4 text-sm text-muted-foreground">
            No hay facturas registradas.
          </div>
        )}
      </div>

      {/* Desktop view - Table */}
      <div className="hidden md:block rounded-lg border border-border bg-card shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          {loading && (
            <div className="p-4 text-sm text-muted-foreground">Cargando facturas...</div>
          )}
          {!loading && error && (
            <div className="p-4 text-sm text-destructive">{error}</div>
          )}
          {!loading && !error && (
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
                {filteredInvoices.map((venta) => (
                  <tr
                    key={venta.id}
                    className="border-b border-border hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-medium">{venta.number}</td>
                    <td className="px-4 py-3 text-sm">
                      {venta.date_display || venta.date}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {clientLookup[venta.client] || "Sin cliente"}
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-primary/10 text-primary font-medium">
                        {venta.doc_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">{venta.payment_method}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getDteBadgeStyle(
                          venta.dte_status,
                        )}`}
                      >
                        {getDteDisplayStatus(venta.dte_status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">${Number(venta.total).toFixed(2)}</td>
                    <td className="px-4 py-3 text-right flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenEdit(venta)}
                      >
                        <Pencil className="h-4 w-4" />
                        <span className="sr-only">Editar</span>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteInvoice(venta.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                        <span className="sr-only">Eliminar</span>
                      </Button>
                    </td>
                  </tr>
                ))}
                {filteredInvoices.length === 0 && (
                  <tr>
                    <td
                      className="px-4 py-3 text-sm text-muted-foreground"
                      colSpan={8}
                    >
                      No hay facturas registradas.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <ServiceSelectorModal
        open={showServiceSelectorModal}
        onCancel={handleCancelSelection}
        onConfirm={handleConfirmServices}
        services={services}
        initialSelected={selectedServices}
      />

      <NuevaFacturaModal
        open={showNuevaFacturaModal}
        onOpenChange={(open) => {
          if (!open) {
            handleCancelSelection();
          } else {
            setShowNuevaFacturaModal(true);
          }
        }}
        onSubmit={handleSaveInvoice}
        clients={clients}
        invoice={selectedInvoice}
        mode={mode}
        selectedServices={selectedServices}
        onCancel={handleCancelSelection}
      />

      <Dialog open={showExportModal} onOpenChange={setShowExportModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Exportar libro de ventas</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Tipo de DTE</Label>
              <Select
                value={exportDteType}
                onValueChange={(value) =>
                  setExportDteType(
                    value as "consumidores" | "contribuyentes"
                  )
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="consumidores">Consumidores finales</SelectItem>
                  <SelectItem value="contribuyentes">
                    Crédito fiscal (contribuyentes)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Mes</Label>
              <Select
                value={exportMonth}
                onValueChange={(value) => setExportMonth(value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona mes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Enero</SelectItem>
                  <SelectItem value="2">Febrero</SelectItem>
                  <SelectItem value="3">Marzo</SelectItem>
                  <SelectItem value="4">Abril</SelectItem>
                  <SelectItem value="5">Mayo</SelectItem>
                  <SelectItem value="6">Junio</SelectItem>
                  <SelectItem value="7">Julio</SelectItem>
                  <SelectItem value="8">Agosto</SelectItem>
                  <SelectItem value="9">Septiembre</SelectItem>
                  <SelectItem value="10">Octubre</SelectItem>
                  <SelectItem value="11">Noviembre</SelectItem>
                  <SelectItem value="12">Diciembre</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowExportModal(false)}>
              Cancelar
            </Button>
            <Button onClick={handleDownload}>Descargar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
