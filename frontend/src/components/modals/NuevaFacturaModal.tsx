import { useEffect, useMemo, useState } from "react";
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

const IVA_RATE = 0.13;
const PRICE_OVERRIDE_ACCESS_CODE = "123";

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
  const [serviceLines, setServiceLines] = useState<
    (SelectedServicePayload & {
      unit_price: number;
      original_unit_price: number;
      price_overridden: boolean;
      override_authorized: boolean;
      access_code: string;
      show_access_code: boolean;
    })[]
  >([]);

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
        const priceWithVat = Number(item.unit_price) || 0;
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
        description: "Debe agregar al menos un servicio",
        variant: "destructive",
      });
      return;
    }

    const servicesPayload: SelectedServicePayload[] = serviceLines.map((item) => {
      const price = Number(item.unit_price);
      return {
        service_id: item.service_id,
        name: item.name,
        price,
        original_unit_price: item.original_unit_price,
        unit_price: price,
        price_overridden: item.price_overridden,
        quantity: item.quantity,
        subtotal: Number((price * item.quantity).toFixed(2)),
        ...(item.price_overridden ? { override_code: item.access_code } : {}),
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
      setServiceLines(
        selectedServices.map((item) => {
          const originalPrice = Number(
            item.original_unit_price ?? item.unit_price ?? item.price ?? 0,
          );
          const appliedPrice = Number(item.unit_price ?? item.price ?? originalPrice);
          const priceOverridden = item.price_overridden ?? appliedPrice !== originalPrice;
          return {
            ...item,
            original_unit_price: originalPrice,
            unit_price: appliedPrice,
            price_overridden: priceOverridden,
            override_authorized: false,
            access_code: "",
            show_access_code: priceOverridden,
            subtotal: Number((appliedPrice * item.quantity).toFixed(2)),
          };
        }),
      );
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
    updater: (
      item: (SelectedServicePayload & {
        unit_price: number;
        original_unit_price: number;
        price_overridden: boolean;
        override_authorized: boolean;
        access_code: string;
        show_access_code: boolean;
      }),
    ) => SelectedServicePayload & {
      unit_price: number;
      original_unit_price: number;
      price_overridden: boolean;
      override_authorized: boolean;
      access_code: string;
      show_access_code: boolean;
    },
  ) => {
    setServiceLines((prev) =>
      prev.map((item) => (item.service_id === serviceId ? updater(item) : item)),
    );
  };

  const handleAuthorizeOverride = (serviceId: number) => {
    const target = serviceLines.find((item) => item.service_id === serviceId);
    if (!target) return;

    if (target.access_code !== PRICE_OVERRIDE_ACCESS_CODE) {
      toast({
        title: "Código incorrecto",
        description: "El código de acceso no es válido para modificar el precio.",
        variant: "destructive",
      });
      updateServiceLine(serviceId, (item) => ({
        ...item,
        access_code: "",
        show_access_code: true,
        override_authorized: false,
      }));
      return;
    }

    updateServiceLine(serviceId, (item) => ({
      ...item,
      override_authorized: true,
      show_access_code: false,
    }));
  };

  const handlePriceChange = (serviceId: number, value: string) => {
    const parsed = Number(value);
    if (!isFinite(parsed)) return;

    updateServiceLine(serviceId, (item) => {
      if (!item.override_authorized) {
        return { ...item, show_access_code: true };
      }

      if (parsed <= 0) {
        toast({
          title: "Precio inválido",
          description: "El precio debe ser mayor a 0.",
          variant: "destructive",
        });
        return { ...item, unit_price: item.original_unit_price, price_overridden: false };
      }

      const priceOverridden = parsed !== item.original_unit_price;
      return {
        ...item,
        unit_price: parsed,
        price_overridden: priceOverridden,
        subtotal: Number((parsed * item.quantity).toFixed(2)),
      };
    });
  };

  const handleResetPrice = (serviceId: number) => {
    updateServiceLine(serviceId, (item) => ({
      ...item,
      unit_price: item.original_unit_price,
      price_overridden: false,
      override_authorized: false,
      access_code: "",
      show_access_code: false,
      subtotal: Number((item.original_unit_price * item.quantity).toFixed(2)),
    }));
  };

  const handleDialogChange = (value: boolean) => {
    if (!value) {
      onCancel();
    } else {
      onOpenChange(value);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleDialogChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "edit" ? "Editar Factura" : "Nueva Factura"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmitForm)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tipoDTE">Tipo de DTE</Label>
              <Select
                value={form.watch("tipoDTE")}
                onValueChange={(value) =>
                  form.setValue("tipoDTE", value as "CF" | "CCF" | "SX")
                }
              >
                <SelectTrigger>
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
              <Popover open={clientOpen} onOpenChange={setClientOpen}>
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
                <PopoverContent className="w-full p-0" align="start">
                  <Command className="max-h-72">
                    <CommandInput
                      placeholder="Buscar cliente…"
                      value={clientSearch}
                      onValueChange={setClientSearch}
                    />
                    <CommandEmpty>No se encontraron clientes</CommandEmpty>
                    <CommandGroup className="max-h-60 overflow-y-auto">
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

            <div className="md:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <Label>Resumen de servicios</Label>
                <span className="text-sm text-muted-foreground">
                  Total: ${total.toFixed(2)}
                </span>
              </div>

              {serviceLines.length > 0 ? (
                <div className="space-y-3">
                  <div className="hidden sm:block overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium">Servicio</th>
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
                            <td className="px-4 py-3 text-center">{servicio.quantity}</td>
                            <td className="px-4 py-3">
                              <div className="space-y-2">
                                <div className="text-xs text-muted-foreground">
                                  <span
                                    className={
                                      servicio.price_overridden ? "line-through" : ""
                                    }
                                  >
                                    Original: ${Number(servicio.original_unit_price).toFixed(2)}
                                  </span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <Input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    className="w-32"
                                    value={servicio.unit_price}
                                    disabled={!servicio.override_authorized}
                                    onChange={(event) =>
                                      handlePriceChange(
                                        servicio.service_id,
                                        event.target.value,
                                      )
                                    }
                                    onFocus={() =>
                                      updateServiceLine(servicio.service_id, (item) => ({
                                        ...item,
                                        show_access_code: true,
                                      }))
                                    }
                                  />
                                  {servicio.price_overridden && (
                                    <span className="rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                                      Modificado
                                    </span>
                                  )}
                                  {!servicio.override_authorized && !servicio.price_overridden && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      onClick={() =>
                                        updateServiceLine(servicio.service_id, (item) => ({
                                          ...item,
                                          show_access_code: true,
                                        }))
                                      }
                                    >
                                      Modificar
                                    </Button>
                                  )}
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleResetPrice(servicio.service_id)}
                                  >
                                    Restablecer
                                  </Button>
                                </div>
                                {(servicio.show_access_code || servicio.price_overridden) && (
                                  <div className="flex items-center gap-2">
                                    <Input
                                      type="password"
                                      placeholder="Código de acceso"
                                      className="w-40"
                                      value={servicio.access_code}
                                      onChange={(event) =>
                                        updateServiceLine(servicio.service_id, (item) => ({
                                          ...item,
                                          access_code: event.target.value,
                                        }))
                                      }
                                    />
                                    <Button
                                      type="button"
                                      size="sm"
                                      onClick={() => handleAuthorizeOverride(servicio.service_id)}
                                    >
                                      Validar
                                    </Button>
                                  </div>
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
                        className="rounded-lg border border-border p-3 space-y-2"
                      >
                        <p className="text-sm font-medium leading-tight">{servicio.name}</p>
                        <p className="text-xs text-muted-foreground">
                          ID: {renderCellValue(servicio.service_id)}
                        </p>
                        <div className="flex items-center justify-between text-sm">
                          <span>Cantidad:</span>
                          <span className="font-medium">{servicio.quantity}</span>
                        </div>
                        <div className="space-y-2">
                          <div className="text-xs text-muted-foreground">
                            <span
                              className={
                                servicio.price_overridden ? "line-through" : ""
                              }
                            >
                              Original: ${Number(servicio.original_unit_price).toFixed(2)}
                            </span>
                          </div>
                          <Input
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={servicio.unit_price}
                            disabled={!servicio.override_authorized}
                            onChange={(event) =>
                              handlePriceChange(servicio.service_id, event.target.value)
                            }
                          />
                          {servicio.price_overridden && (
                            <span className="inline-flex w-fit rounded-full bg-warning/10 px-2 py-0.5 text-xs font-medium text-warning">
                              Modificado
                            </span>
                          )}
                          {!servicio.override_authorized && !servicio.price_overridden && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                updateServiceLine(servicio.service_id, (item) => ({
                                  ...item,
                                  show_access_code: true,
                                }))
                              }
                            >
                              Modificar
                            </Button>
                          )}
                          {(servicio.show_access_code || servicio.price_overridden) && (
                            <div className="flex items-center gap-2">
                              <Input
                                type="password"
                                placeholder="Código de acceso"
                                value={servicio.access_code}
                                onChange={(event) =>
                                  updateServiceLine(servicio.service_id, (item) => ({
                                    ...item,
                                    access_code: event.target.value,
                                  }))
                                }
                              />
                              <Button
                                type="button"
                                size="sm"
                                onClick={() => handleAuthorizeOverride(servicio.service_id)}
                              >
                                Validar
                              </Button>
                            </div>
                          )}
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => handleResetPrice(servicio.service_id)}
                          >
                            Restablecer
                          </Button>
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
                  Selecciona servicios antes de crear la factura.
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
            <div className="space-y-2 bg-muted/50 p-4 rounded-lg">
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

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={submitting || serviceLines.length === 0}>
              {mode === "edit" ? "Guardar Cambios" : "Crear Factura"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
