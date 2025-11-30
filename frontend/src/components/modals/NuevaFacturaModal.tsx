import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Trash2 } from "lucide-react";
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
  services: Service[];
  invoice?: Invoice | null;
  mode?: "create" | "edit";
}

interface ServicioSeleccionado {
  serviceId: number;
  nombre: string;
  precio: number;
  cantidad: number;
  subtotal: number;
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
  const [busquedaServicio, setBusquedaServicio] = useState("");
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

  const agregarServicio = (servicio: Service) => {
    setServiciosSeleccionados((prev) => {
      const indexExistente = prev.findIndex(
        (item) => item.serviceId === servicio.id,
      );

      if (indexExistente !== -1) {
        const actualizados = [...prev];
        const cantidad = actualizados[indexExistente].cantidad + 1;
        actualizados[indexExistente].cantidad = cantidad;
        actualizados[indexExistente].subtotal =
          Number(actualizados[indexExistente].precio) * cantidad;
        return actualizados;
      }

      return [
        ...prev,
        {
          serviceId: servicio.id,
          nombre: servicio.name,
          precio: Number(servicio.base_price),
          cantidad: 1,
          subtotal: Number(servicio.base_price),
        },
      ];
    });
    setBusquedaServicio("");
  };

  const eliminarServicio = (index: number) => {
    setServiciosSeleccionados((prev) => prev.filter((_, i) => i !== index));
  };

  const actualizarCantidad = (index: number, cantidad: number) => {
    setServiciosSeleccionados((prev) => {
      const nuevosServicios = [...prev];
      if (!nuevosServicios[index]) return prev;

      const cantidadActualizada = Math.max(1, cantidad);
      nuevosServicios[index] = {
        ...nuevosServicios[index],
        cantidad: cantidadActualizada,
        subtotal: Number(
          (nuevosServicios[index].precio * cantidadActualizada).toFixed(2),
        ),
      };
      return nuevosServicios;
    });
  };

  const calcularSubtotal = () => {
    return serviciosSeleccionados.reduce(
      (acc, s) => acc + s.subtotal,
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

    const servicesPayload: SelectedServicePayload[] = serviciosSeleccionados.map(
      (item) => ({
        serviceId: item.serviceId,
        name: item.nombre,
        price: item.precio,
        quantity: item.cantidad,
        subtotal: Number((item.precio * item.cantidad).toFixed(2)),
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
      setServiciosSeleccionados([]);
      setBusquedaServicio("");
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

  const serviciosFiltrados = useMemo(() => {
    const query = busquedaServicio.toLowerCase().trim();
    return services.filter((servicio) => {
      if (!query) return true;
      const textoBusqueda = `${servicio.name} ${servicio.code}`.toLowerCase();
      return textoBusqueda.includes(query);
    });
  }, [busquedaServicio, services]);

  const agregarPrimeraCoincidencia = () => {
    if (!busquedaServicio.trim() || serviciosFiltrados.length === 0) return;
    agregarServicio(serviciosFiltrados[0]);
  };

  useEffect(() => {
    if (mode === "edit" && invoice) {
      form.reset({
        date: invoice.date,
        clienteId: invoice.client.toString(),
        tipoDTE: invoice.doc_type,
        metodoPago: invoice.payment_method as PaymentMethod,
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
            subtotal: Number(item.subtotal) ||
              Number((Number(item.unit_price) * item.quantity).toFixed(2)),
          };
        }),
      );
      setBusquedaServicio("");
    }

    if (mode === "create" && open) {
      form.reset({
        date: new Date().toISOString().split("T")[0],
        clienteId: "",
        tipoDTE: "CF",
        metodoPago: "Efectivo",
      });
      setServiciosSeleccionados([]);
      setBusquedaServicio("");
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
              <div className="space-y-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <Label htmlFor="buscarServicio">Servicios</Label>
                  <div className="relative w-full sm:max-w-xs">
                    <Input
                      id="buscarServicio"
                      placeholder="Buscar servicio por nombre o texto"
                      value={busquedaServicio}
                      onChange={(e) => setBusquedaServicio(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          agregarPrimeraCoincidencia();
                        }
                      }}
                    />

                    <div className="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-md border border-border bg-background shadow-md">
                      {serviciosFiltrados.length > 0 ? (
                        <div className="max-h-56 overflow-y-auto">
                          {serviciosFiltrados.map((servicio) => (
                            <button
                              key={servicio.id}
                              type="button"
                              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-muted"
                              onClick={() => agregarServicio(servicio)}
                            >
                              <span className="font-medium">{servicio.name}</span>
                              <span className="text-xs text-muted-foreground">
                                ${Number(servicio.base_price).toFixed(2)} · {servicio.code}
                              </span>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="px-3 py-2 text-sm text-muted-foreground">
                          No se encontraron servicios
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {serviciosSeleccionados.length > 0 ? (
                <div className="space-y-3">
                  <div className="hidden overflow-hidden rounded-lg border border-border sm:block">
                    <div className="overflow-x-auto scrollbar-thin">
                      <table className="w-full min-w-[600px]">
                        <thead className="bg-muted/50">
                          <tr className="border-b border-border">
                            <th className="px-3 py-3 text-left text-sm font-medium min-w-[180px]">
                              Servicio
                            </th>
                            <th className="px-3 py-3 text-right text-sm font-medium w-[120px]">
                              Precio
                            </th>
                            <th className="px-3 py-3 text-center text-sm font-medium w-[140px]">
                              Cantidad
                            </th>
                            <th className="px-3 py-3 text-right text-sm font-medium w-[120px]">
                              Subtotal
                            </th>
                            <th className="px-3 py-3 text-center text-sm font-medium w-[80px]">
                              Quitar
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {serviciosSeleccionados.map((servicio, index) => (
                            <tr key={servicio.serviceId} className="border-b border-border">
                              <td className="px-3 py-3 text-sm">{servicio.nombre}</td>
                              <td className="px-3 py-3 text-right text-sm whitespace-nowrap">
                                ${servicio.precio.toFixed(2)}
                              </td>
                              <td className="px-3 py-3 text-center">
                                <div className="inline-flex items-center gap-2">
                                  <Button
                                    type="button"
                                    size="icon"
                                    variant="outline"
                                    className="h-8 w-8"
                                    onClick={() =>
                                      actualizarCantidad(index, Math.max(1, servicio.cantidad - 1))
                                    }
                                  >
                                    -
                                  </Button>
                                  <Input
                                    type="number"
                                    min="1"
                                    value={servicio.cantidad}
                                    onChange={(e) =>
                                      actualizarCantidad(
                                        index,
                                        Math.max(1, Number(e.target.value) || 1),
                                      )
                                    }
                                    className="w-16 text-center"
                                  />
                                  <Button
                                    type="button"
                                    size="icon"
                                    variant="outline"
                                    className="h-8 w-8"
                                    onClick={() => actualizarCantidad(index, servicio.cantidad + 1)}
                                  >
                                    +
                                  </Button>
                                </div>
                              </td>
                              <td className="px-3 py-3 text-right text-sm font-medium whitespace-nowrap">
                                {servicio.subtotal.toFixed(2)}
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

                  <div className="space-y-2 sm:hidden">
                    {serviciosSeleccionados.map((servicio, index) => (
                      <div
                        key={servicio.serviceId}
                        className="rounded-lg border border-border p-3 space-y-2"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium leading-tight">{servicio.nombre}</p>
                            <p className="text-xs text-muted-foreground">
                              Código: {services.find((s) => s.id === servicio.serviceId)?.code || "-"}
                            </p>
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => eliminarServicio(index)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm">
                          <span className="font-medium">${servicio.precio.toFixed(2)}</span>
                          <div className="inline-flex items-center gap-2">
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              className="h-8 w-8"
                              onClick={() =>
                                actualizarCantidad(index, Math.max(1, servicio.cantidad - 1))
                              }
                            >
                              -
                            </Button>
                            <Input
                              type="number"
                              min="1"
                              value={servicio.cantidad}
                              onChange={(e) =>
                                actualizarCantidad(
                                  index,
                                  Math.max(1, Number(e.target.value) || 1),
                                )
                              }
                              className="w-16 text-center"
                            />
                            <Button
                              type="button"
                              size="icon"
                              variant="outline"
                              className="h-8 w-8"
                              onClick={() => actualizarCantidad(index, servicio.cantidad + 1)}
                            >
                              +
                            </Button>
                          </div>
                          <span className="ml-auto font-medium">
                            Subtotal: {servicio.subtotal.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Agrega servicios para verlos aquí.
                </p>
              )}
            </div>
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
