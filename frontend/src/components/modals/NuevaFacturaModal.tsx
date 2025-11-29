import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X, Plus, Trash2 } from "lucide-react";
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
import { Service } from "@/types/service";
import {
  DteStatus,
  Invoice,
  InvoicePayload,
  InvoiceDocType,
  PaymentMethod,
} from "@/types/invoice";

const facturaSchema = z.object({
  number: z.string().min(1, "Debe ingresar un número de factura"),
  date: z.string().min(1, "Debe seleccionar una fecha"),
  clienteId: z.string().min(1, "Debe seleccionar un cliente"),
  tipoDTE: z.enum(["CF", "CCF", "SX"], {
    required_error: "Debe seleccionar un tipo de DTE",
  }),
  metodoPago: z.enum(["Efectivo", "Tarjeta", "Transferencia", "Cheque"], {
    required_error: "Debe seleccionar un método de pago",
  }),
  estadoDTE: z.enum(["Aprobado", "Pendiente", "Rechazado"], {
    required_error: "Debe seleccionar un estado DTE",
  }),
});

interface NuevaFacturaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: InvoicePayload) => Promise<void>;
  clients: Client[];
  services: Service[];
  invoice?: Invoice | null;
  mode?: "create" | "edit";
}

interface ServicioSeleccionado {
  serviceId: number;
  nombre: string;
  precio: number;
  cantidad: number;
}

export function NuevaFacturaModal({
  open,
  onOpenChange,
  onSubmit,
  clients,
  services,
  invoice,
  mode = "create",
}: NuevaFacturaModalProps) {
  const [serviciosSeleccionados, setServiciosSeleccionados] = useState<ServicioSeleccionado[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<z.infer<typeof facturaSchema>>({
    resolver: zodResolver(facturaSchema),
    defaultValues: {
      number: "",
      date: new Date().toISOString().split("T")[0],
      tipoDTE: "CF",
      metodoPago: "Efectivo",
      estadoDTE: "Pendiente",
    },
  });

  const agregarServicio = (servicioId: string) => {
    const servicio = services.find((s) => s.id === parseInt(servicioId, 10));
    if (servicio) {
      setServiciosSeleccionados((prev) => [
        ...prev,
        {
          serviceId: servicio.id,
          nombre: servicio.name,
          precio: Number(servicio.base_price),
          cantidad: 1,
        },
      ]);
    }
  };

  const eliminarServicio = (index: number) => {
    setServiciosSeleccionados(serviciosSeleccionados.filter((_, i) => i !== index));
  };

  const actualizarCantidad = (index: number, cantidad: number) => {
    const nuevosServicios = [...serviciosSeleccionados];
    nuevosServicios[index].cantidad = cantidad;
    setServiciosSeleccionados(nuevosServicios);
  };

  const calcularSubtotal = () => {
    return serviciosSeleccionados.reduce(
      (acc, s) => acc + s.precio * s.cantidad,
      0
    );
  };

  const calcularIVA = () => {
    const subtotal = calcularSubtotal();
    return subtotal * 0.13;
  };

  const calcularTotal = () => {
    return calcularSubtotal() + calcularIVA();
  };

  const onSubmitForm = async (data: z.infer<typeof facturaSchema>) => {
    if (serviciosSeleccionados.length === 0) {
      toast({
        title: "Error",
        description: "Debe agregar al menos un servicio",
        variant: "destructive",
      });
      return;
    }

    const itemsPayload = serviciosSeleccionados.map((item) => ({
      service: item.serviceId,
      quantity: item.cantidad,
      unit_price: item.precio,
      subtotal: Number((item.precio * item.cantidad).toFixed(2)),
    }));

    const payload: InvoicePayload = {
      number: data.number,
      date: data.date,
      client: parseInt(data.clienteId, 10),
      doc_type: data.tipoDTE as InvoiceDocType,
      payment_method: data.metodoPago as PaymentMethod,
      dte_status: data.estadoDTE as DteStatus,
      total: Number(calcularTotal().toFixed(2)),
      items: itemsPayload,
    };

    try {
      setSubmitting(true);
      await onSubmit(payload);
      toast({
        title: mode === "edit" ? "Factura actualizada" : "Factura creada",
        description: "La factura se ha guardado correctamente",
      });
      form.reset({
        number: "",
        date: new Date().toISOString().split("T")[0],
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
        estadoDTE: "Pendiente",
      });
      setServiciosSeleccionados([]);
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
        number: invoice.number,
        date: invoice.date,
        clienteId: invoice.client.toString(),
        tipoDTE: invoice.doc_type,
        metodoPago: invoice.payment_method as PaymentMethod,
        estadoDTE: invoice.dte_status as DteStatus,
      });

      const items = invoice.items || [];
      setServiciosSeleccionados(
        items.map((item) => {
          const service = services.find((s) => s.id === item.service);
          return {
            serviceId: item.service,
            nombre: service?.name || `Servicio ${item.service}`,
            precio: Number(item.unit_price),
            cantidad: item.quantity,
          };
        }),
      );
    }

    if (mode === "create" && open) {
      form.reset({
        number: "",
        date: new Date().toISOString().split("T")[0],
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
        estadoDTE: "Pendiente",
      });
      setServiciosSeleccionados([]);
    }
  }, [invoice, mode, open, services, form]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "edit" ? "Editar Factura" : "Nueva Factura"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmitForm)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="number">Número de factura</Label>
              <Input
                id="number"
                placeholder="DTE-000001"
                {...form.register("number")}
              />
              {form.formState.errors.number && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.number.message}
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

            <div className="space-y-2">
              <Label htmlFor="estadoDTE">Estado DTE</Label>
              <Select
                value={form.watch("estadoDTE")}
                onValueChange={(value) =>
                  form.setValue("estadoDTE", value as DteStatus)
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Aprobado">Aprobado</SelectItem>
                  <SelectItem value="Pendiente">Pendiente</SelectItem>
                  <SelectItem value="Rechazado">Rechazado</SelectItem>
                </SelectContent>
              </Select>
              {form.formState.errors.estadoDTE && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.estadoDTE.message}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label>Servicios</Label>
              <Select onValueChange={agregarServicio}>
                <SelectTrigger className="w-[250px]">
                  <Plus className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Agregar servicio" />
                </SelectTrigger>
                <SelectContent>
                  {services
                    .filter(
                      (s) =>
                        !serviciosSeleccionados.find(
                          (ss) => ss.serviceId === s.id,
                        ),
                    )
                    .map((servicio) => (
                      <SelectItem key={servicio.id} value={servicio.id.toString()}>
                        {servicio.name} - $
                        {Number(servicio.base_price).toFixed(2)}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>

            {serviciosSeleccionados.length > 0 && (
              <div className="border border-border rounded-lg overflow-hidden">
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="w-full min-w-[600px]">
                    <thead className="bg-muted/50">
                      <tr className="border-b border-border">
                        <th className="px-3 py-3 text-left text-sm font-medium min-w-[180px]">
                          Servicio
                        </th>
                        <th className="px-3 py-3 text-center text-sm font-medium w-[100px]">
                          Cantidad
                        </th>
                        <th className="px-3 py-3 text-right text-sm font-medium w-[100px]">
                          Precio
                        </th>
                        <th className="px-3 py-3 text-right text-sm font-medium w-[100px]">
                          Subtotal
                        </th>
                        <th className="px-3 py-3 text-center text-sm font-medium w-[80px]">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                  <tbody>
                      {serviciosSeleccionados.map((servicio, index) => (
                        <tr key={index} className="border-b border-border">
                          <td className="px-3 py-3 text-sm">{servicio.nombre}</td>
                          <td className="px-3 py-3 text-center">
                            <Input
                              type="number"
                              min="1"
                              value={servicio.cantidad}
                              onChange={(e) =>
                                actualizarCantidad(index, parseInt(e.target.value))
                              }
                              className="w-16 mx-auto"
                            />
                          </td>
                          <td className="px-3 py-3 text-right text-sm whitespace-nowrap">
                            ${servicio.precio.toFixed(2)}
                          </td>
                          <td className="px-3 py-3 text-right text-sm font-medium whitespace-nowrap">
                            ${(servicio.precio * servicio.cantidad).toFixed(2)}
                          </td>
                          <td className="px-3 py-3 text-center">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => eliminarServicio(index)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {serviciosSeleccionados.length > 0 && (
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
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={submitting}>
              {mode === "edit" ? "Guardar Cambios" : "Crear Factura"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
