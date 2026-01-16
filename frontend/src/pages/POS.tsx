import { useEffect, useMemo, useState } from "react";
import {
  Ban,
  Copy,
  Download,
  FilePlus2,
  Filter,
  Mail,
  MessageCircle,
  Plus,
  RefreshCw,
} from "lucide-react";
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { NuevaFacturaModal } from "@/components/modals/NuevaFacturaModal";
import { ServiceSelectorModal } from "@/components/modals/ServiceSelectorModal";
import { API_BASE_URL, api } from "@/lib/api";
import { getInvoiceDateInfo, InvoiceDateFilter } from "@/lib/dates";
import { Client } from "@/types/client";
import { Invoice, InvoiceItem, InvoicePayload, SelectedServicePayload } from "@/types/invoice";
import { Service } from "@/types/service";
import { toast } from "@/hooks/use-toast";

const getDteBadgeStyle = (status: string | undefined) => {
  const normalized = status?.toUpperCase();
  if (normalized === "ACEPTADO") {
    return "bg-success/10 text-success";
  }
  if (normalized === "INVALIDADO") {
    return "bg-muted text-muted-foreground";
  }
  if (normalized === "RECHAZADO" || normalized === "ERROR") {
    return "bg-destructive/10 text-destructive";
  }
  return "bg-warning/10 text-warning";
};

const getDteDisplayStatus = (status: string | undefined) => {
  const normalized = status?.toUpperCase();
  if (normalized === "ACEPTADO") return "ACEPTADO";
  if (normalized === "INVALIDADO") return "INVALIDADO";
  if (normalized === "RECHAZADO") return "RECHAZADO";
  if (normalized === "PENDIENTE") return "Pendiente";
  return status || "";
};

const isPendingStatus = (status: string | undefined) => {
  return status?.toUpperCase() === "PENDIENTE";
};

const isAcceptedStatus = (status: string | undefined) => {
  return status?.toUpperCase() === "ACEPTADO";
};

const getInvoiceTipo = (invoice: Invoice): string => {
  const tipo =
    invoice.tipo ??
    invoice.type ??
    invoice.dte_tipo ??
    invoice.dte?.tipoDte ??
    invoice.dte?.tipo ??
    invoice.doc_type;
  return String(tipo ?? "").toUpperCase();
};

const getNumeroControlUpper = (invoice: Invoice): string => {
  const value = invoice.numero_control || invoice.numeroControl;
  return value ? String(value).toUpperCase() : "—";
};

const getCodigoGeneracionRaw = (invoice: Invoice): string | null => {
  const value = invoice.codigo_generacion || invoice.codigoGeneracion;
  return value ? String(value) : null;
};

const getCodigoGeneracionUpper = (invoice: Invoice): string => {
  const value = getCodigoGeneracionRaw(invoice);
  return value ? value.toUpperCase() : "—";
};

const isCCFInvoice = (invoice: Invoice): boolean => {
  const tipo = getInvoiceTipo(invoice);
  return tipo === "CCF" || tipo === "03";
};

const copyText = async (text: string, onSuccess: () => void, onError: () => void) => {
  try {
    await navigator.clipboard.writeText(text);
    onSuccess();
  } catch (error) {
    console.error("Error al copiar al portapapeles", error);
    try {
      const el = document.createElement("textarea");
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      onSuccess();
    } catch (fallbackError) {
      console.error("Error al copiar en fallback", fallbackError);
      onError();
    }
  }
};

const resolveClientId = (client: Invoice["client"]): number | undefined => {
  if (typeof client === "object" && client !== null) {
    return client.id;
  }
  return client;
};

const resolveServiceFromItem = (
  item: InvoiceItem,
  services: Service[],
): { serviceId?: number; serviceDetails?: Service } => {
  if (typeof item.service === "object" && item.service !== null) {
    return { serviceId: item.service.id, serviceDetails: item.service };
  }
  const serviceDetails = services.find((service) => service.id === item.service);
  return { serviceId: item.service, serviceDetails };
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
  const [showInvalidationModal, setShowInvalidationModal] = useState(false);
  const [invalidationInvoice, setInvalidationInvoice] = useState<Invoice | null>(null);
  const [tipoAnulacion, setTipoAnulacion] = useState("2");
  const [motivoAnulacion, setMotivoAnulacion] = useState("");
  const [invalidating, setInvalidating] = useState(false);

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
        if (normalizedStatus === "ACEPTADO") {
          toast({
            title: "Factura creada",
            description:
              invoice.dte_message || "Factura creada y DTE aceptado por Hacienda.",
          });
        } else if (
          normalizedStatus === "RECHAZADO" ||
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
            description: invoice.dte_message || "DTE pendiente de envío o procesamiento.",
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

  const getInvoiceDateLabel = (invoice: Invoice): string => {
    const { dateString, formatted } = getInvoiceDateInfo(invoice);
    return formatted ?? dateString ?? "—";
  };

  const filteredInvoices = useMemo(() => {
    const referenceDate = new Date();
    return invoices.filter((invoice) => {
      const clientId = resolveClientId(invoice.client);
      const matchesSearch = `${invoice.number} ${clientLookup[clientId ?? -1] || ""}`
        .toLowerCase()
        .includes(search.toLowerCase());

      if (!matchesSearch) return false;

      const { dateString, matchesFilter } = getInvoiceDateInfo(invoice);
      if (!dateString) return false;
      return matchesFilter(filter as InvoiceDateFilter, referenceDate);
    });
  }, [clientLookup, filter, invoices, search]);

  const totalInvoicesAmount = useMemo(() => {
    return filteredInvoices.reduce((sum, invoice) => {
      if (!isAcceptedStatus(invoice.dte_status)) {
        return sum;
      }
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
      const { serviceId, serviceDetails } = resolveServiceFromItem(item, services);
      const originalPrice = Number(
        item.original_unit_price ?? item.unit_price ?? serviceDetails?.base_price ?? 0,
      );
      const price = Number(item.unit_price || originalPrice);
      const quantity = item.quantity || 1;
      return {
        service_id: serviceId ?? 0,
        name: serviceDetails?.name || `Producto ${serviceId ?? ""}`,
        price,
        original_unit_price: originalPrice,
        unit_price: price,
        price_overridden: price !== originalPrice,
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

  const handlePlaceholderAction = (title: string, description: string) => {
    toast({ title, description });
  };

  const handleCopyCodigo = (codigo: string) => {
    const safeToast = typeof toast === "function";
    copyText(
      codigo.toUpperCase(),
      () => {
        if (safeToast) {
          toast({
            title: "Copiado",
            description: "Código de generación copiado al portapapeles.",
          });
        } else {
          console.log("Código de generación copiado al portapapeles.");
        }
      },
      () => {
        if (safeToast) {
          toast({
            title: "Error",
            description: "No se pudo copiar el código de generación.",
            variant: "destructive",
          });
        } else {
          console.log("No se pudo copiar el código de generación.");
        }
      },
    );
  };

  const handleResendDte = async (invoice: Invoice) => {
    try {
      const response = await api.post<Invoice>(`/invoices/${invoice.id}/resend-dte/`);
      const updatedInvoice = response.data;
      toast({
        title: "Reenvío iniciado",
        description:
          updatedInvoice.dte_message ||
          "El DTE pendiente se está reenviando automáticamente.",
      });
      await fetchInitialData();
    } catch (err) {
      console.error("Error al reenviar DTE", err);
      toast({
        title: "No se pudo reenviar el DTE",
        description: "Intenta nuevamente en unos momentos.",
        variant: "destructive",
      });
    }
  };

  const handleOpenInvalidation = (invoice: Invoice) => {
    setInvalidationInvoice(invoice);
    setTipoAnulacion("2");
    setMotivoAnulacion("");
    setShowInvalidationModal(true);
  };

  const resolveInvalidationMessage = (status: string | undefined, message?: string) => {
    switch (status) {
      case "INVALIDADO":
      case "ACEPTADO":
        return {
          title: "Invalidación aceptada",
          description: message || "La factura fue invalidada correctamente.",
        };
      case "RECHAZADO":
        return {
          title: "Invalidación rechazada",
          description: message || "Hacienda rechazó la invalidación. Revisa los datos.",
          variant: "destructive" as const,
        };
      case "ERROR_PUENTE":
        return {
          title: "Error del puente",
          description: message || "El puente devolvió un error. Intenta nuevamente.",
          variant: "destructive" as const,
        };
      case "PENDIENTE":
        return {
          title: "Invalidación pendiente",
          description: message || "La invalidación quedó pendiente por conexión.",
        };
      case "BLOQUEADO":
        return {
          title: "No se puede invalidar",
          description: message || "La factura no cumple los requisitos para invalidar.",
          variant: "destructive" as const,
        };
      case "CONFIG_FALTANTE":
        return {
          title: "Configuración faltante",
          description:
            message ||
            "DTE_API_BASE_URL no configurada. Configure la URL del puente DTE para invalidación.",
          variant: "destructive" as const,
        };
      case "NO_AUTENTICADO":
        return {
          title: "No autenticado",
          description: message || "No autenticado contra el puente DTE.",
          variant: "destructive" as const,
        };
      default:
        return {
          title: "Estado de invalidación",
          description: message || "La invalidación se procesó con estado desconocido.",
        };
    }
  };

  const handleConfirmInvalidation = async () => {
    if (!invalidationInvoice) return;
    setInvalidating(true);
    try {
      const response = await api.post(
        `/invoices/${invalidationInvoice.id}/invalidate-dte/`,
        {
          tipoAnulacion: Number(tipoAnulacion) || 2,
          motivoAnulacion: motivoAnulacion.trim(),
        },
      );

      const statusValue = String(response.data?.status || "").toUpperCase();
      const messageValue = response.data?.message || response.data?.detail;
      const toastInfo = resolveInvalidationMessage(statusValue, messageValue);
      toast(toastInfo);
      await fetchInitialData();
      setShowInvalidationModal(false);
    } catch (err: any) {
      const statusValue = String(err?.response?.data?.status || "").toUpperCase();
      const messageValue =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        "No se pudo invalidar el DTE.";
      const bridgeBody = err?.response?.data?.details?.bridge_body;
      if (bridgeBody) {
        console.error("INVALIDACION bridge_body:", bridgeBody);
      }
      const bridgeSnippet =
        typeof bridgeBody === "string"
          ? bridgeBody.slice(0, 200)
          : bridgeBody
          ? JSON.stringify(bridgeBody).slice(0, 200)
          : "";
      const toastInfo = resolveInvalidationMessage(statusValue || "RECHAZADO", messageValue);
      if (bridgeSnippet) {
        toastInfo.description = `${toastInfo.description}\n${bridgeSnippet}`;
      }
      toast(toastInfo);
    } finally {
      setInvalidating(false);
    }
  };

  const renderInvoiceActions = (invoice: Invoice) => {
    const codigo = getCodigoGeneracionRaw(invoice);
    const showInvalidar = isAcceptedStatus(invoice.dte_status);
    const showNotaCredito = isCCFInvoice(invoice);
    const showResend = isPendingStatus(invoice.dte_status);

    return (
      <div className="flex items-center justify-end gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Enviar por WhatsApp"
              onClick={() =>
                handlePlaceholderAction(
                  "Próximamente",
                  "Enviar DTE por WhatsApp (pendiente).",
                )
              }
            >
              <MessageCircle className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Enviar por WhatsApp</TooltipContent>
        </Tooltip>

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Enviar por correo"
              onClick={() =>
                handlePlaceholderAction(
                  "Próximamente",
                  "Enviar DTE por correo (pendiente).",
                )
              }
            >
              <Mail className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Enviar por correo</TooltipContent>
        </Tooltip>

        {showInvalidar && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Invalidar DTE"
                onClick={() => handleOpenInvalidation(invoice)}
              >
                <Ban className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Invalidar</TooltipContent>
          </Tooltip>
        )}

        {showNotaCredito && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Nota de crédito (solo CCF)"
                onClick={() =>
                  handlePlaceholderAction(
                    "Próximamente",
                    "Nota de crédito CCF (pendiente).",
                  )
                }
              >
                <FilePlus2 className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Nota de crédito (solo CCF)</TooltipContent>
          </Tooltip>
        )}

        {showResend && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Reenviar DTE pendiente"
                onClick={() => handleResendDte(invoice)}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reenviar DTE pendiente</TooltipContent>
          </Tooltip>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <span>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Copiar código de generación"
                disabled={!codigo}
                onClick={() => codigo && handleCopyCodigo(codigo)}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {codigo ? "Copiar código de generación" : "Sin código de generación"}
          </TooltipContent>
        </Tooltip>
      </div>
    );
  };

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
                    {getInvoiceDateLabel(venta)}
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
                    {clientLookup[resolveClientId(venta.client) ?? -1] || "Sin cliente"}
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
              <div className="flex justify-end mt-3">
                {renderInvoiceActions(venta)}
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
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Número de Control
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Fecha</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">Cliente</th>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Código de Generación
                  </th>
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
                    <td className="px-4 py-3 font-medium">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="block max-w-[180px] truncate whitespace-nowrap">
                            {getNumeroControlUpper(venta)}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent>{getNumeroControlUpper(venta)}</TooltipContent>
                      </Tooltip>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {getInvoiceDateLabel(venta)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {clientLookup[resolveClientId(venta.client) ?? -1] || "Sin cliente"}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">
                      {getCodigoGeneracionUpper(venta)}
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
                    <td className="px-4 py-3 text-right">
                      {renderInvoiceActions(venta)}
                    </td>
                  </tr>
                ))}
                {filteredInvoices.length === 0 && (
                  <tr>
                    <td
                      className="px-4 py-3 text-sm text-muted-foreground"
                      colSpan={9}
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

      <Dialog
        open={showInvalidationModal}
        onOpenChange={(open) => {
          setShowInvalidationModal(open);
          if (!open) {
            setInvalidationInvoice(null);
          }
        }}
      >
        <DialogContent className="flex w-[95vw] max-h-[85vh] max-w-3xl flex-col overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Invalidar DTE</DialogTitle>
          </DialogHeader>
          <div className="flex-1 space-y-4 overflow-y-auto py-2">
            <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">
              <p className="font-semibold">No se puede deshacer.</p>
            </div>
            <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div>
                <p className="text-muted-foreground">Número de control</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <p className="break-all whitespace-pre-wrap font-medium">
                    {invalidationInvoice ? getNumeroControlUpper(invalidationInvoice) : "—"}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Código de generación</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <p className="break-all whitespace-pre-wrap font-medium">
                    {invalidationInvoice ? getCodigoGeneracionUpper(invalidationInvoice) : "—"}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Cliente</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <p className="break-all whitespace-pre-wrap font-medium">
                    {invalidationInvoice
                      ? clientLookup[resolveClientId(invalidationInvoice.client) ?? -1] ||
                        "Sin cliente"
                      : "—"}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Fecha emisión (fecEmi)</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <p className="break-all whitespace-pre-wrap font-medium">
                    {invalidationInvoice?.fec_emi ||
                      invalidationInvoice?.issue_date ||
                      (invalidationInvoice ? getInvoiceDateLabel(invalidationInvoice) : "—")}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Tipo DTE</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <p className="break-all whitespace-pre-wrap font-medium">
                    {invalidationInvoice ? getInvoiceTipo(invalidationInvoice) : "—"}
                  </p>
                </div>
              </div>
              <div>
                <p className="text-muted-foreground">Sello recibido</p>
                <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
                  <div className="overflow-x-auto">
                    <p className="break-all whitespace-pre-wrap font-medium">
                      {invalidationInvoice?.sello_recibido || "—"}
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Tipo de anulación</Label>
              <Select value={tipoAnulacion} onValueChange={setTipoAnulacion}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 - Error en la información</SelectItem>
                  <SelectItem value="2">2 - Rescindir operación</SelectItem>
                  <SelectItem value="3">3 - Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Motivo (opcional)</Label>
              <Input
                value={motivoAnulacion}
                onChange={(e) => setMotivoAnulacion(e.target.value)}
                placeholder="Describe el motivo de la anulación"
              />
            </div>
          </div>
          <DialogFooter className="sticky bottom-0 gap-2 border-t border-border bg-background/80 p-4 backdrop-blur">
            <Button
              variant="outline"
              onClick={() => setShowInvalidationModal(false)}
              disabled={invalidating}
            >
              Cancelar
            </Button>
            <Button onClick={handleConfirmInvalidation} disabled={invalidating}>
              {invalidating ? "Enviando..." : "Confirmar invalidación"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
