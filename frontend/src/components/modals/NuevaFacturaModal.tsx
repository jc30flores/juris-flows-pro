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
import { toast } from "@/hooks/use-toast";
import { Client } from "@/types/client";
import {
  Invoice,
  InvoicePayload,
  InvoiceDocType,
  PaymentMethod,
  SelectedServicePayload,
} from "@/types/invoice";

const facturaSchema = z.object({
  date: z.string().min(1, "Debe seleccionar una fecha"),
  clienteId: z.string().min(1, "Debe seleccionar un cliente"),
  tipoDTE: z.enum(["CF", "CCF", "SX"], {
    required_error: "Debe seleccionar un tipo de DTE",
  }),
  metodoPago: z.enum(["Efectivo", "Tarjeta", "Transferencia", "Cheque"], {
    required_error: "Debe seleccionar un método de pago",
  }),
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

  const form = useForm<z.infer<typeof facturaSchema>>({
    resolver: zodResolver(facturaSchema),
    defaultValues: {
      date: new Date().toISOString().split("T")[0],
      tipoDTE: "CF",
      metodoPago: "Efectivo",
      clienteId: "",
    },
  });

  const calcularSubtotal = () => {
    return selectedServices.reduce((acc, s) => acc + Number(s.subtotal), 0);
  };

  const calcularIVA = () => {
    const subtotal = calcularSubtotal();
    return subtotal * 0.13;
  };

  const calcularTotal = () => {
    return calcularSubtotal() + calcularIVA();
  };

  const onSubmitForm = async (data: z.infer<typeof facturaSchema>) => {
    if (selectedServices.length === 0) {
      toast({
        title: "Error",
        description: "Debe agregar al menos un servicio",
        variant: "destructive",
      });
      return;
    }

    const servicesPayload: SelectedServicePayload[] = selectedServices.map(
      (item) => ({
        serviceId: item.serviceId,
        name: item.name,
        price: item.price,
        quantity: item.quantity,
        subtotal: Number((item.price * item.quantity).toFixed(2)),
      }),
    );

    const payload: InvoicePayload = {
      date: data.date,
      client: parseInt(data.clienteId, 10),
      doc_type: data.tipoDTE as InvoiceDocType,
      payment_method: data.metodoPago as PaymentMethod,
      total: Number(calcularTotal().toFixed(2)),
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
        date: new Date().toISOString().split("T")[0],
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
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
      })),
    [clients],
  );

  useEffect(() => {
    if (mode === "edit" && invoice) {
      form.reset({
        date: invoice.date,
        clienteId: invoice.client.toString(),
        tipoDTE: invoice.doc_type,
        metodoPago: invoice.payment_method as PaymentMethod,
      });
    }

    if (mode === "create" && open) {
      form.reset({
        date: new Date().toISOString().split("T")[0],
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
      });
    }
  }, [invoice, mode, open, form]);

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
              <Select
                value={form.watch("clienteId")}
                onValueChange={(value) => form.setValue("clienteId", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar cliente" />
                </SelectTrigger>
                <SelectContent>
                  {clientesOptions.map((cliente) => (
                    <SelectItem key={cliente.id} value={cliente.id}>
                      {cliente.nombre} ({cliente.tipo})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
                  Total: ${calcularTotal().toFixed(2)}
                </span>
              </div>

              {selectedServices.length > 0 ? (
                <div className="space-y-3">
                  <div className="hidden sm:block overflow-x-auto rounded-lg border border-border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-3 text-left font-medium">Servicio</th>
                          <th className="px-4 py-3 text-center font-medium">Cantidad</th>
                          <th className="px-4 py-3 text-right font-medium">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedServices.map((servicio) => (
                          <tr key={servicio.serviceId} className="border-t border-border">
                            <td className="px-4 py-3">
                              <p className="font-medium leading-tight">{servicio.name}</p>
                              <p className="text-xs text-muted-foreground">ID: {servicio.serviceId}</p>
                            </td>
                            <td className="px-4 py-3 text-center">{servicio.quantity}</td>
                            <td className="px-4 py-3 text-right font-semibold">
                              ${Number(servicio.subtotal).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="grid gap-3 sm:hidden">
                    {selectedServices.map((servicio) => (
                      <div
                        key={servicio.serviceId}
                        className="rounded-lg border border-border p-3 space-y-1"
                      >
                        <p className="text-sm font-medium leading-tight">{servicio.name}</p>
                        <p className="text-xs text-muted-foreground">ID: {servicio.serviceId}</p>
                        <div className="flex items-center justify-between text-sm">
                          <span>Cantidad:</span>
                          <span className="font-medium">{servicio.quantity}</span>
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

          {selectedServices.length > 0 && (
            <div className="space-y-2 bg-muted/50 p-4 rounded-lg">
              <div className="flex justify-between text-sm">
                <span>Subtotal:</span>
                <span className="font-medium">${calcularSubtotal().toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>IVA (13%):</span>
                <span className="font-medium">${calcularIVA().toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold border-t border-border pt-2">
                <span>Total:</span>
                <span>${calcularTotal().toFixed(2)}</span>
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
            <Button type="submit" disabled={submitting || selectedServices.length === 0}>
              {mode === "edit" ? "Guardar Cambios" : "Crear Factura"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
