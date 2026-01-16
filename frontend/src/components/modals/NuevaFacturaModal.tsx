import { useEffect, useMemo, useRef, useState } from "react";
import { Pencil, RotateCcw } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { toast } from "@/hooks/use-toast";
import { Client } from "@/types/client";
import {
  Invoice,
  InvoicePayload,
  InvoiceDocType,
  PaymentMethod,
  SelectedServicePayload,
} from "@/types/invoice";
import { Textarea } from "@/components/ui/textarea";
import { renderCellValue } from "@/lib/render";
import { getElSalvadorDateString } from "@/lib/dates";
import { api } from "@/lib/api";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const IVA_RATE = 0.13;
const AUTHORIZATION_WINDOW_MS = 5 * 60 * 1000;

type PriceType = "UNIT" | "WHOLESALE";

type ServiceLine = SelectedServicePayload & {
  price_type: PriceType;
  price_type_override: boolean;
  unit_price_snapshot: number;
  wholesale_price_snapshot: number | null;
  applied_unit_price: number;
  applied_price_draft: string;
  price_overridden: boolean;
  price_error?: string | null;
  isEditable: boolean;
};

const round2 = (value: number): number => {
  if (!isFinite(value)) return 0;
  // ROUND HALF UP: si el tercer decimal >= 5, sube el segundo
  return Math.round((value + Number.EPSILON) * 100) / 100;
};

const splitGrossAmount = (gross: number) => {
  // gross = total con IVA incluido
  const grossRounded = round2(gross); // Aseguramos 2 decimales base
  const baseUnrounded = grossRounded / (1 + IVA_RATE);
  const ivaUnrounded = grossRounded - baseUnrounded;

  const iva = round2(ivaUnrounded); // redondeo correcto de IVA
  const subtotal = round2(grossRounded - iva); // lo que queda es la base

  return { subtotal, iva, total: grossRounded };
};

const resolveBasePrice = (line: ServiceLine, type: PriceType) => {
  const unitPrice = Number(line.unit_price_snapshot || 0);
  const wholesaleRaw = line.wholesale_price_snapshot;
  const wholesalePrice =
    wholesaleRaw === null || wholesaleRaw === undefined
      ? null
      : Number(wholesaleRaw);

  if (type === "WHOLESALE") {
    if (wholesalePrice !== null && isFinite(wholesalePrice)) {
      return { value: wholesalePrice, isFallback: false };
    }
    return { value: unitPrice, isFallback: true };
  }

  return { value: unitPrice, isFallback: false };
};

const facturaSchema = z.object({
  date: z.string().min(1, "Debe seleccionar una fecha"),
  clienteId: z.string().min(1, "Debe seleccionar un cliente"),
  tipoDTE: z.enum(["CF", "CCF", "SX"], {
    required_error: "Debe seleccionar un tipo de DTE",
  }),
  metodoPago: z.enum(["Efectivo", "Tarjeta", "Transferencia", "Cheque"], {
    required_error: "Debe seleccionar un método de pago",
  }),
  observations: z.string().optional(),
});

interface AccessCodeModalProps {
  open: boolean;
  value: string;
  error?: string | null;
  onChange: (value: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

const AccessCodeModal = ({
  open,
  value,
  error,
  onChange,
  onConfirm,
  onCancel,
}: AccessCodeModalProps) => (
  <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
    <DialogContent className="max-w-sm">
      <DialogHeader>
        <DialogTitle>Código de acceso requerido</DialogTitle>
      </DialogHeader>
      <form autoComplete="off" className="space-y-3">
        <Label htmlFor="accessCode">Código de acceso</Label>
        <Input
          id="accessCode"
          name="access_code"
          type="password"
          placeholder="Ingresa el código"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="off"
          autoCapitalize="off"
          autoCorrect="off"
          spellCheck={false}
          inputMode="numeric"
          data-lpignore="true"
          data-form-type="other"
        />
        {error && <p className="text-sm text-destructive">{error}</p>}
      </form>
      <DialogFooter className="gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="button" onClick={onConfirm}>
          Confirmar
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
);

interface NuevaFacturaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: InvoicePayload) => Promise<void>;
  clients: Client[];
  invoice?: Invoice | null;
  mode?: "create" | "edit";
  selectedServices: SelectedServicePayload[];
  onCancel: () => void;
}

export function NuevaFacturaModal({
  open,
  onOpenChange,
  onSubmit,
  clients,
  invoice,
  mode = "create",
  selectedServices,
  onCancel,
}: NuevaFacturaModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const [clientSearch, setClientSearch] = useState("");
  const [clientOpen, setClientOpen] = useState(false);
  const [serviceLines, setServiceLines] = useState<ServiceLine[]>([]);
  const [globalPriceType, setGlobalPriceType] = useState<PriceType>("UNIT");
  const [authorizedUntil, setAuthorizedUntil] = useState<number | null>(null);
  const [overrideToken, setOverrideToken] = useState<string | null>(null);
  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [accessCodeInput, setAccessCodeInput] = useState("");
  const [accessError, setAccessError] = useState<string | null>(null);
  const [selectedLineId, setSelectedLineId] = useState<number | null>(null);
  const priceInputRefs = useRef<Record<number, HTMLInputElement | null>>({});
  const dialogContainerRef = useRef<HTMLDivElement | null>(null);

  const resolveClientId = (client: Invoice["client"]): string => {
    if (typeof client === "object" && client !== null) {
      return client.id.toString();
    }
    return client.toString();
  };

  const form = useForm<z.infer<typeof facturaSchema>>({
    resolver: zodResolver(facturaSchema),
    defaultValues: {
      date: getElSalvadorDateString(),
      tipoDTE: "CF",
      metodoPago: "Efectivo",
      clienteId: "",
      observations: "",
    },
  });

  const grossTotal = useMemo(
    () =>
      serviceLines.reduce((sum, item) => {
        const qty = Number(item.quantity) || 0;
        const priceWithVat = Number(item.applied_unit_price) || 0;
        return sum + qty * priceWithVat;
      }, 0),
    [serviceLines],
  );

  const { subtotal, iva, total } = useMemo(
    () => splitGrossAmount(grossTotal),
    [grossTotal],
  );

  const onSubmitForm = async (data: z.infer<typeof facturaSchema>) => {
    if (serviceLines.length === 0) {
      toast({
        title: "Error",
        description: "Debe agregar al menos un producto",
        variant: "destructive",
      });
      return;
    }

    const normalizedLines = serviceLines.map((item) => {
      const draftValue = item.applied_price_draft.trim();
      const basePrice = resolveBasePrice(item, item.price_type).value;
      const fallbackValue = basePrice;
      const parsed = draftValue === "" ? fallbackValue : Number(draftValue);

      if (!isFinite(parsed) || parsed < 0) {
        return { ...item, price_error: "El precio debe ser mayor o igual a 0." };
      }

      const priceOverridden = parsed !== basePrice;
      return {
        ...item,
        applied_unit_price: parsed,
        applied_price_draft: parsed.toFixed(2),
        price_overridden: priceOverridden,
        price_error: null,
        subtotal: Number((parsed * item.quantity).toFixed(2)),
      };
    });

    const invalidLines = normalizedLines.filter(
      (item) => !isFinite(item.applied_unit_price) || item.applied_unit_price < 0,
    );
    if (invalidLines.length > 0) {
      setServiceLines(normalizedLines);
      return;
    }

    setServiceLines(normalizedLines);

    const hasOverride = normalizedLines.some((item) => item.price_overridden);
    if (hasOverride) {
      const now = Date.now();
      if (!overrideToken || !authorizedUntil || now > authorizedUntil) {
        toast({
          title: "Autorización requerida",
          description: "Debe autorizar la modificación de precio antes de guardar.",
          variant: "destructive",
        });
        return;
      }
    }

    const servicesPayload: SelectedServicePayload[] = normalizedLines.map((item) => {
      const price = Number(item.applied_unit_price);
      return {
        service_id: item.service_id,
        name: item.name,
        price,
        unit_price_snapshot: item.unit_price_snapshot,
        wholesale_price_snapshot: item.wholesale_price_snapshot,
        unit_price: price,
        applied_unit_price: price,
        price_type: item.price_type,
        price_overridden: item.price_overridden,
        quantity: item.quantity,
        line_subtotal: Number((price * item.quantity).toFixed(2)),
        subtotal: Number((price * item.quantity).toFixed(2)),
      };
    });

    const payload: InvoicePayload = {
      date: data.date,
      client: parseInt(data.clienteId, 10),
      doc_type: data.tipoDTE as InvoiceDocType,
      payment_method: data.metodoPago as PaymentMethod,
      total,
      observations: data.observations || "",
      services: servicesPayload,
      ...(hasOverride && overrideToken ? { override_token: overrideToken } : {}),
    };

    try {
      setSubmitting(true);
      await onSubmit(payload);
      toast({
        title: mode === "edit" ? "Factura actualizada" : "Factura creada",
        description: "La factura se ha guardado correctamente",
      });
      form.reset({
        date: getElSalvadorDateString(),
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
        observations: "",
      });
      setAuthorizedUntil(null);
      setOverrideToken(null);
      setSelectedLineId(null);
      onOpenChange(false);
    } catch (error) {
      console.error("Error al guardar factura", error);
      toast({
        title: "No se pudo guardar la factura",
        description: "Intente nuevamente o verifique los datos ingresados.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const clientesOptions = useMemo(
    () =>
      clients.map((cliente) => ({
        id: cliente.id.toString(),
        nombre: cliente.company_name || cliente.full_name,
        tipo: cliente.client_type,
        nit: cliente.nit || "",
        nrc: cliente.nrc || "",
        dui: cliente.dui || "",
      })),
    [clients],
  );

  const selectedClientId = form.watch("clienteId");
  const selectedClient = useMemo(() => {
    return clientesOptions.find((cliente) => cliente.id === selectedClientId) || null;
  }, [clientesOptions, selectedClientId]);

  const normalizeText = (value: string): string =>
    value
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();

  const filteredClients = useMemo(() => {
    const query = normalizeText(clientSearch);
    if (!query) return clientesOptions.slice(0, 20);
    return clientesOptions
      .filter((cliente) => {
        const haystack = [
          cliente.nombre,
          cliente.nit,
          cliente.nrc,
          cliente.dui,
          cliente.tipo,
        ]
          .filter(Boolean)
          .join(" ");
        return normalizeText(haystack).includes(query);
      })
      .slice(0, 20);
  }, [clientSearch, clientesOptions]);

  useEffect(() => {
    if (open) {
      const preferredGlobal: PriceType =
        selectedServices.length > 0 &&
        selectedServices.every((entry) => (entry.price_type ?? "UNIT") === "WHOLESALE")
          ? "WHOLESALE"
          : "UNIT";
      const mappedLines = selectedServices.map((item) => {
        const unitSnapshot = Number(
          item.unit_price_snapshot ?? item.unit_price ?? item.price ?? 0,
        );
        const wholesaleSnapshot =
          item.wholesale_price_snapshot === undefined
            ? null
            : item.wholesale_price_snapshot;
        const priceType = (item.price_type ?? "UNIT") as PriceType;
        const basePrice = resolveBasePrice(
          {
            ...item,
            unit_price_snapshot: unitSnapshot,
            wholesale_price_snapshot: wholesaleSnapshot,
            price_type: priceType,
            price_type_override: false,
            applied_unit_price: 0,
            applied_price_draft: "",
            price_overridden: false,
            isEditable: false,
          } as ServiceLine,
          priceType,
        ).value;
        const appliedPrice = Number(
          item.applied_unit_price ?? item.unit_price ?? item.price ?? basePrice,
        );
        const priceOverridden = item.price_overridden ?? appliedPrice !== basePrice;
        return {
          ...item,
          unit_price_snapshot: unitSnapshot,
          wholesale_price_snapshot:
            wholesaleSnapshot === null || wholesaleSnapshot === undefined
              ? null
              : Number(wholesaleSnapshot),
          price_type: priceType,
          price_type_override: priceType !== preferredGlobal,
          applied_unit_price: appliedPrice,
          applied_price_draft: appliedPrice.toFixed(2),
          price_overridden: priceOverridden,
          price_error: null,
          subtotal: Number((appliedPrice * item.quantity).toFixed(2)),
          isEditable: false,
        };
      });
      setGlobalPriceType(preferredGlobal);
      setServiceLines(mappedLines);
      setAuthorizedUntil(null);
      setOverrideToken(null);
      setAccessModalOpen(false);
      setAccessCodeInput("");
      setAccessError(null);
      setSelectedLineId(null);
    }

    if (mode === "edit" && invoice) {
      form.reset({
        date: invoice.date,
        clienteId: resolveClientId(invoice.client),
        tipoDTE: invoice.doc_type,
        metodoPago: invoice.payment_method as PaymentMethod,
        observations: invoice.observations || "",
      });
    }

    if (mode === "create" && open) {
      form.reset({
        date: getElSalvadorDateString(),
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
        observations: "",
      });
      setClientSearch("");
      setClientOpen(false);
    }
  }, [invoice, mode, open, form, selectedServices]);

  const updateServiceLine = (
    serviceId: number,
    updater: (item: ServiceLine) => ServiceLine,
  ) => {
    setServiceLines((prev) =>
      prev.map((item) => (item.service_id === serviceId ? updater(item) : item)),
    );
  };

  const applyOverrideValue = (serviceId: number, value: number) => {
    updateServiceLine(serviceId, (item) => {
      const basePrice = resolveBasePrice(item, item.price_type).value;
      const priceOverridden = value !== basePrice;
      const nextValue = priceOverridden ? value : basePrice;
      return {
        ...item,
        applied_unit_price: nextValue,
        applied_price_draft: nextValue.toFixed(2),
        price_overridden: priceOverridden,
        price_error: null,
        subtotal: Number((nextValue * item.quantity).toFixed(2)),
      };
    });
  };

  const handlePriceDraftChange = (serviceId: number, value: string) => {
    updateServiceLine(serviceId, (item) => ({
      ...item,
      applied_price_draft: value,
      price_error: null,
    }));
  };

  const handlePriceBlur = (serviceId: number) => {
    const target = serviceLines.find((item) => item.service_id === serviceId);
    if (!target) return;

    const draftValue = target.applied_price_draft.trim();
    if (draftValue === "") {
      applyOverrideValue(
        serviceId,
        resolveBasePrice(target, target.price_type).value,
      );
      return;
    }

    const parsed = Number(draftValue);
    if (!isFinite(parsed) || parsed < 0) {
      updateServiceLine(serviceId, (item) => ({
        ...item,
        price_error: "El precio debe ser mayor o igual a 0.",
      }));
      return;
    }

    applyOverrideValue(serviceId, parsed);
  };

  const handleResetPrice = (serviceId: number) => {
    const target = serviceLines.find((item) => item.service_id === serviceId);
    if (!target) return;
    applyOverrideValue(
      serviceId,
      resolveBasePrice(target, target.price_type).value,
    );
  };

  const handleQuantityChange = (serviceId: number, value: string) => {
    const parsed = Number(value);
    const safeQuantity = !isFinite(parsed) || parsed <= 0 ? 1 : Math.floor(parsed);
    updateServiceLine(serviceId, (item) => ({
      ...item,
      quantity: safeQuantity,
      subtotal: Number((item.applied_unit_price * safeQuantity).toFixed(2)),
    }));
  };

  const applyPriceTypeChange = (
    serviceId: number,
    nextType: PriceType,
    override: boolean,
  ) => {
    updateServiceLine(serviceId, (item) => {
      const { value: basePrice } = resolveBasePrice(item, nextType);
      const nextApplied = item.price_overridden ? item.applied_unit_price : basePrice;
      const priceOverridden = nextApplied !== basePrice;
      return {
        ...item,
        price_type: nextType,
        price_type_override: override,
        applied_unit_price: nextApplied,
        applied_price_draft: priceOverridden
          ? item.applied_price_draft
          : nextApplied.toFixed(2),
        price_overridden: priceOverridden,
        subtotal: Number((nextApplied * item.quantity).toFixed(2)),
      };
    });
  };

  const handleGlobalPriceTypeChange = (nextType: PriceType) => {
    setGlobalPriceType(nextType);
    setServiceLines((prev) =>
      prev.map((item) => {
        if (item.price_type_override) {
          return item;
        }
        const { value: basePrice } = resolveBasePrice(item, nextType);
        const nextApplied = item.price_overridden ? item.applied_unit_price : basePrice;
        const priceOverridden = nextApplied !== basePrice;
        return {
          ...item,
          price_type: nextType,
          applied_unit_price: nextApplied,
          applied_price_draft: priceOverridden
            ? item.applied_price_draft
            : nextApplied.toFixed(2),
          price_overridden: priceOverridden,
          subtotal: Number((nextApplied * item.quantity).toFixed(2)),
        };
      }),
    );
  };

  const handleAccessConfirm = async () => {
    if (!accessCodeInput.trim()) {
      setAccessError("Ingresa un código válido.");
      return;
    }

    if (selectedLineId === null) {
      setAccessError("Selecciona un producto para desbloquear.");
      return;
    }

    let expiresAt: number | null = null;
    try {
      const response = await api.post("/price-overrides/validate/", {
        code: accessCodeInput.trim(),
      });
      const expiresIn =
        typeof response.data?.expires_in === "number"
          ? response.data.expires_in * 1000
          : AUTHORIZATION_WINDOW_MS;
      expiresAt = Date.now() + expiresIn;
      setOverrideToken(response.data?.token ?? null);
      setAuthorizedUntil(expiresAt);
    } catch (error) {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Código incorrecto. Intenta nuevamente.";
      setAccessError(message);
      return;
    }
    if (!expiresAt) {
      setAccessError("No se pudo determinar la expiración de la autorización.");
      return;
    }

    updateServiceLine(selectedLineId, (item) => ({
      ...item,
      isEditable: true,
    }));
    setAccessModalOpen(false);
    setAccessError(null);
    setAccessCodeInput("");
    const input = priceInputRefs.current[selectedLineId];
    if (input) {
      window.setTimeout(() => {
        input.focus();
        input.select();
      }, 0);
    }
  };

  const handleAccessCancel = () => {
    setAccessModalOpen(false);
    setAccessError(null);
    setAccessCodeInput("");
    setSelectedLineId(null);
  };

  const handleUnlockRequest = (serviceId: number) => {
    setSelectedLineId(serviceId);
    setAccessCodeInput("");
    setAccessModalOpen(true);
  };

  const handleDialogChange = (value: boolean) => {
    if (!value) {
      setServiceLines((prev) =>
        prev.map((item) => ({ ...item, isEditable: false })),
      );
      setAuthorizedUntil(null);
      setOverrideToken(null);
      setAccessModalOpen(false);
      setSelectedLineId(null);
      onCancel();
    } else {
      onOpenChange(value);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleDialogChange}>
        <DialogContent
          ref={(node) => {
            dialogContainerRef.current = node;
          }}
          className="flex h-[90vh] w-[94vw] max-w-none flex-col overflow-visible rounded-2xl p-0 sm:h-auto sm:max-h-[90vh] sm:w-full sm:max-w-3xl"
        >
          <DialogHeader className="sticky top-0 z-10 border-b border-border bg-background/95 px-6 py-4 backdrop-blur">
            <DialogTitle>
              {mode === "edit" ? "Editar Factura" : "Nueva Factura"}
            </DialogTitle>
          </DialogHeader>

        <form
          onSubmit={form.handleSubmit(onSubmitForm)}
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex-1 space-y-6 overflow-y-auto px-6 pb-6 pt-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="tipoDTE">Tipo de DTE</Label>
              <Select
                value={form.watch("tipoDTE")}
                onValueChange={(value) =>
                  form.setValue("tipoDTE", value as "CF" | "CCF" | "SX")
                }
              >
                <SelectTrigger autoFocus>
                  <SelectValue placeholder="Seleccionar tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CF">Consumidor Final (CF)</SelectItem>
                  <SelectItem value="CCF">Crédito Fiscal (CCF)</SelectItem>
                  <SelectItem value="SX">Sujeto Excluido (SX)</SelectItem>
                </SelectContent>
              </Select>
              {form.formState.errors.tipoDTE && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.tipoDTE.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="date">Fecha</Label>
              <Input id="date" type="date" {...form.register("date")} />
              {form.formState.errors.date && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.date.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="clienteId">Cliente</Label>
              <Popover open={clientOpen} onOpenChange={setClientOpen} modal={false}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                  >
                    {selectedClient
                      ? `${selectedClient.nombre} (${selectedClient.tipo})`
                      : "Buscar cliente…"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  align="start"
                  side="bottom"
                  avoidCollisions
                  collisionPadding={8}
                  container={dialogContainerRef.current}
                  className="z-[60] w-[--radix-popover-trigger-width] max-h-[45vh] overflow-y-auto p-0"
                >
                  <Command shouldFilter={false} className="max-h-[45vh] w-full">
                    <CommandInput
                      placeholder="Buscar cliente…"
                      value={clientSearch}
                      onValueChange={setClientSearch}
                    />
                    {clients.length === 0 ? (
                      <div className="p-4 text-sm text-muted-foreground">
                        No hay clientes disponibles.
                      </div>
                    ) : (
                      <CommandEmpty>No se encontraron clientes</CommandEmpty>
                    )}
                    <CommandGroup className="max-h-[35vh] overflow-y-auto">
                      {filteredClients.map((cliente) => {
                        const secondary = cliente.nrc || cliente.nit || cliente.dui;
                        return (
                          <CommandItem
                            key={cliente.id}
                            value={`${cliente.nombre}-${cliente.id}`}
                            onSelect={() => {
                              form.setValue("clienteId", cliente.id, {
                                shouldValidate: true,
                              });
                              setClientOpen(false);
                              setClientSearch("");
                            }}
                          >
                            <div className="flex flex-col">
                              <span className="font-medium">
                                {cliente.nombre} ({cliente.tipo})
                              </span>
                              {secondary && (
                                <span className="text-xs text-muted-foreground">
                                  {secondary}
                                </span>
                              )}
                            </div>
                          </CommandItem>
                        );
                      })}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
              {form.formState.errors.clienteId && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.clienteId.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="metodoPago">Método de Pago</Label>
              <Select
                value={form.watch("metodoPago")}
                onValueChange={(value) =>
                  form.setValue("metodoPago", value as PaymentMethod)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar método" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Efectivo">Efectivo</SelectItem>
                  <SelectItem value="Tarjeta">Tarjeta</SelectItem>
                  <SelectItem value="Transferencia">Transferencia</SelectItem>
                  <SelectItem value="Cheque">Cheque</SelectItem>
                </SelectContent>
              </Select>
              {form.formState.errors.metodoPago && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.metodoPago.message}
                </p>
              )}
            </div>

            <div className="sm:col-span-2 space-y-4">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Label>Resumen de productos</Label>
                  <span className="text-sm text-muted-foreground">
                    Total: ${total.toFixed(2)}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs text-muted-foreground">Precio global:</span>
                  <div className="inline-flex items-center rounded-full border border-border bg-muted/40 p-1">
                    <Button
                      type="button"
                      size="sm"
                      variant={globalPriceType === "UNIT" ? "secondary" : "ghost"}
                      className="h-7 rounded-full px-3 text-xs"
                      onClick={() => handleGlobalPriceTypeChange("UNIT")}
                    >
                      Unitario
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant={globalPriceType === "WHOLESALE" ? "secondary" : "ghost"}
                      className="h-7 rounded-full px-3 text-xs"
                      onClick={() => handleGlobalPriceTypeChange("WHOLESALE")}
                    >
                      Mayoreo
                    </Button>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Aplica a líneas sin override.
                  </span>
                </div>
              </div>

              {serviceLines.length > 0 ? (
                <div className="space-y-3">
                  <div className="hidden sm:block overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium">Producto</th>
                          <th className="px-4 py-3 text-center font-medium">Cantidad</th>
                          <th className="px-4 py-3 text-left font-medium">Precio</th>
                          <th className="px-4 py-3 text-right font-medium">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        {serviceLines.map((servicio) => (
                          <tr key={servicio.service_id} className="border-t border-border">
                            <td className="px-4 py-3">
                              <p className="font-medium leading-tight">{servicio.name}</p>
                              <p className="text-xs text-muted-foreground">
                                ID: {renderCellValue(servicio.service_id)}
                              </p>
                            </td>
                            <td className="px-4 py-3 text-center">
                              <Input
                                type="number"
                                min="1"
                                step="1"
                                className="mx-auto w-20 text-center shadow-inner"
                                value={servicio.quantity}
                                onChange={(event) =>
                                  handleQuantityChange(
                                    servicio.service_id,
                                    event.target.value,
                                  )
                                }
                              />
                            </td>
                            <td className="px-4 py-3">
                              <div className="space-y-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <div className="inline-flex items-center rounded-full border border-border bg-muted/40 p-1 text-xs">
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant={
                                        servicio.price_type === "UNIT" ? "secondary" : "ghost"
                                      }
                                      className="h-6 rounded-full px-2 text-[11px]"
                                      onClick={() =>
                                        applyPriceTypeChange(
                                          servicio.service_id,
                                          "UNIT",
                                          "UNIT" !== globalPriceType,
                                        )
                                      }
                                    >
                                      Unit
                                    </Button>
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant={
                                        servicio.price_type === "WHOLESALE"
                                          ? "secondary"
                                          : "ghost"
                                      }
                                      className="h-6 rounded-full px-2 text-[11px]"
                                      onClick={() =>
                                        applyPriceTypeChange(
                                          servicio.service_id,
                                          "WHOLESALE",
                                          "WHOLESALE" !== globalPriceType,
                                        )
                                      }
                                    >
                                      May
                                    </Button>
                                  </div>
                                  <span className="text-xs text-muted-foreground">
                                    {servicio.price_type_override ? "Override" : "Global"}
                                  </span>
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {(() => {
                                    const { value, isFallback } = resolveBasePrice(
                                      servicio,
                                      servicio.price_type,
                                    );
                                    const label =
                                      servicio.price_type === "WHOLESALE"
                                        ? "Mayoreo"
                                        : "Unitario";
                                    return (
                                      <>
                                        <span
                                          className={
                                            servicio.price_overridden ? "line-through" : ""
                                          }
                                        >
                                          Original ({label}): ${value.toFixed(2)}
                                        </span>
                                        {servicio.price_type === "WHOLESALE" && isFallback && (
                                          <span className="block text-amber-500">
                                            Mayoreo no definido, usando unitario.
                                          </span>
                                        )}
                                      </>
                                    );
                                  })()}
                                </div>
                                <div className="flex items-center gap-2">
                                  <Input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    className="w-32 shadow-inner"
                                    value={servicio.applied_price_draft}
                                    disabled={!servicio.isEditable}
                                    ref={(node) => {
                                      priceInputRefs.current[servicio.service_id] = node;
                                    }}
                                    onChange={(event) =>
                                      handlePriceDraftChange(
                                        servicio.service_id,
                                        event.target.value,
                                      )
                                    }
                                    onBlur={() => handlePriceBlur(servicio.service_id)}
                                  />
                                  <div className="flex items-center gap-1">
                                    {!servicio.isEditable && (
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Button
                                            type="button"
                                            variant="ghost"
                                            size="icon"
                                            aria-label="Editar precio"
                                            onClick={() => handleUnlockRequest(servicio.service_id)}
                                          >
                                            <Pencil className="h-4 w-4" />
                                          </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>Editar precio</TooltipContent>
                                      </Tooltip>
                                    )}
                                    {(() => {
                                      const money = (value: number | string) =>
                                        Number((Number(value) || 0).toFixed(2));
                                      const basePrice = resolveBasePrice(
                                        servicio,
                                        servicio.price_type,
                                      ).value;
                                      const isPriceChanged =
                                        money(servicio.applied_unit_price) !==
                                        money(basePrice);
                                      if (!isPriceChanged) {
                                        return null;
                                      }
                                      return (
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <Button
                                              type="button"
                                              variant="ghost"
                                              size="icon"
                                              aria-label="Restablecer precio"
                                              onClick={() => handleResetPrice(servicio.service_id)}
                                            >
                                              <RotateCcw className="h-4 w-4" />
                                            </Button>
                                          </TooltipTrigger>
                                          <TooltipContent>Restablecer precio</TooltipContent>
                                        </Tooltip>
                                      );
                                    })()}
                                  </div>
                                </div>
                                {servicio.price_error && (
                                  <p className="text-xs text-destructive">
                                    {servicio.price_error}
                                  </p>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right font-semibold">
                              ${Number(servicio.subtotal).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="grid gap-3 sm:hidden">
                    {serviceLines.map((servicio) => (
                      <div
                        key={servicio.service_id}
                        className="space-y-2 rounded-lg border border-border p-3"
                      >
                        <p className="text-sm font-medium leading-tight">{servicio.name}</p>
                        <p className="text-xs text-muted-foreground">
                          ID: {renderCellValue(servicio.service_id)}
                        </p>
                        <div className="flex items-center justify-between text-sm">
                          <span>Cantidad:</span>
                          <Input
                            type="number"
                            min="1"
                            step="1"
                            className="w-20 text-center shadow-inner"
                            value={servicio.quantity}
                            onChange={(event) =>
                              handleQuantityChange(
                                servicio.service_id,
                                event.target.value,
                              )
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <div className="inline-flex items-center rounded-full border border-border bg-muted/40 p-1 text-xs">
                              <Button
                                type="button"
                                size="sm"
                                variant={
                                  servicio.price_type === "UNIT" ? "secondary" : "ghost"
                                }
                                className="h-6 rounded-full px-2 text-[11px]"
                                onClick={() =>
                                  applyPriceTypeChange(
                                    servicio.service_id,
                                    "UNIT",
                                    "UNIT" !== globalPriceType,
                                  )
                                }
                              >
                                Unit
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant={
                                  servicio.price_type === "WHOLESALE"
                                    ? "secondary"
                                    : "ghost"
                                }
                                className="h-6 rounded-full px-2 text-[11px]"
                                onClick={() =>
                                  applyPriceTypeChange(
                                    servicio.service_id,
                                    "WHOLESALE",
                                    "WHOLESALE" !== globalPriceType,
                                  )
                                }
                              >
                                May
                              </Button>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {servicio.price_type_override ? "Override" : "Global"}
                            </span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {(() => {
                              const { value, isFallback } = resolveBasePrice(
                                servicio,
                                servicio.price_type,
                              );
                              const label =
                                servicio.price_type === "WHOLESALE"
                                  ? "Mayoreo"
                                  : "Unitario";
                              return (
                                <>
                                  <span
                                    className={
                                      servicio.price_overridden ? "line-through" : ""
                                    }
                                  >
                                    Original ({label}): ${value.toFixed(2)}
                                  </span>
                                  {servicio.price_type === "WHOLESALE" && isFallback && (
                                    <span className="block text-amber-500">
                                      Mayoreo no definido, usando unitario.
                                    </span>
                                  )}
                                </>
                              );
                            })()}
                          </div>
                          <Input
                            type="number"
                            step="0.01"
                            min="0"
                            value={servicio.applied_price_draft}
                            disabled={!servicio.isEditable}
                            className="shadow-inner"
                            ref={(node) => {
                              priceInputRefs.current[servicio.service_id] = node;
                            }}
                            onChange={(event) =>
                              handlePriceDraftChange(
                                servicio.service_id,
                                event.target.value,
                              )
                            }
                            onBlur={() => handlePriceBlur(servicio.service_id)}
                          />
                          <div className="flex items-center gap-1">
                            {!servicio.isEditable && (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    aria-label="Editar precio"
                                    onClick={() => handleUnlockRequest(servicio.service_id)}
                                  >
                                    <Pencil className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>Editar precio</TooltipContent>
                              </Tooltip>
                            )}
                            {(() => {
                              const money = (value: number | string) =>
                                Number((Number(value) || 0).toFixed(2));
                              const isPriceChanged =
                                money(servicio.applied_unit_price) !==
                                money(
                                  resolveBasePrice(
                                    servicio,
                                    servicio.price_type,
                                  ).value,
                                );
                              if (!isPriceChanged) {
                                return null;
                              }
                              return (
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      aria-label="Restablecer precio"
                                      onClick={() => handleResetPrice(servicio.service_id)}
                                    >
                                      <RotateCcw className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>Restablecer precio</TooltipContent>
                                </Tooltip>
                              );
                            })()}
                          </div>
                          {servicio.price_error && (
                            <p className="text-xs text-destructive">
                              {servicio.price_error}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span>Subtotal:</span>
                          <span className="font-semibold">${Number(servicio.subtotal).toFixed(2)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Selecciona productos antes de crear la factura.
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="observations">Observaciones</Label>
            <Textarea
              id="observations"
              placeholder="Comentarios u observaciones adicionales"
              rows={3}
              {...form.register("observations")}
            />
          </div>

          {serviceLines.length > 0 && (
            <div className="space-y-2 rounded-lg bg-muted/50 p-4">
              <div className="flex justify-between text-sm">
                <span>Subtotal:</span>
                <span className="font-medium">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>IVA (13%):</span>
                <span className="font-medium">${iva.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold border-t border-border pt-2">
                <span>Total:</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </div>
          )}
          </div>
          <DialogFooter className="sticky bottom-0 z-10 flex-col-reverse gap-2 border-t border-border bg-background/95 px-6 py-4 backdrop-blur sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className="w-full sm:w-auto"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={submitting || serviceLines.length === 0}
              className="w-full sm:w-auto"
            >
              {mode === "edit" ? "Guardar Cambios" : "Crear Factura"}
            </Button>
          </DialogFooter>
        </form>
        </DialogContent>
      </Dialog>
      <AccessCodeModal
        open={accessModalOpen}
        value={accessCodeInput}
        error={accessError}
        onChange={setAccessCodeInput}
        onConfirm={handleAccessConfirm}
        onCancel={handleAccessCancel}
      />
    </>
  );
}
