import { useState } from "react";
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

const facturaSchema = z.object({
  clienteId: z.string().min(1, "Debe seleccionar un cliente"),
  tipoDTE: z.enum(["CF", "CCF", "SX"], {
    required_error: "Debe seleccionar un tipo de DTE",
  }),
  metodoPago: z.string().min(1, "Debe seleccionar un método de pago"),
});

interface NuevaFacturaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ServicioSeleccionado {
  id: number;
  nombre: string;
  precio: number;
  cantidad: number;
}

export function NuevaFacturaModal({ open, onOpenChange }: NuevaFacturaModalProps) {
  const [serviciosSeleccionados, setServiciosSeleccionados] = useState<ServicioSeleccionado[]>([]);

  const form = useForm<z.infer<typeof facturaSchema>>({
    resolver: zodResolver(facturaSchema),
    defaultValues: {
      tipoDTE: "CF",
      metodoPago: "Efectivo",
    },
  });

  // Mock data - en producción vendría de la base de datos
  const clientes = [
    { id: "1", nombre: "Juan Pérez", tipo: "CF" },
    { id: "2", nombre: "Empresa ABC S.A.", tipo: "CCF" },
    { id: "3", nombre: "María González", tipo: "SX" },
  ];

  const servicios = [
    { id: 1, nombre: "Compra Venta de Vehículos", precio: 150.0 },
    { id: 2, nombre: "Escritura Pública: Compra Venta de Inmuebles", precio: 450.0 },
    { id: 3, nombre: "Escritura Pública: Promesa de Venta", precio: 300.0 },
    { id: 4, nombre: "Compra Venta de Arma de Fuego", precio: 120.0 },
    { id: 5, nombre: "Autenticación de Documentos", precio: 50.0 },
  ];

  const agregarServicio = (servicioId: string) => {
    const servicio = servicios.find((s) => s.id === parseInt(servicioId));
    if (servicio) {
      setServiciosSeleccionados([
        ...serviciosSeleccionados,
        { ...servicio, cantidad: 1 },
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

  const onSubmit = (data: z.infer<typeof facturaSchema>) => {
    if (serviciosSeleccionados.length === 0) {
      toast({
        title: "Error",
        description: "Debe agregar al menos un servicio",
        variant: "destructive",
      });
      return;
    }

    console.log({
      ...data,
      servicios: serviciosSeleccionados,
      subtotal: calcularSubtotal(),
      iva: calcularIVA(),
      total: calcularTotal(),
    });

    toast({
      title: "Factura creada",
      description: "La factura se ha creado exitosamente",
    });

    form.reset();
    setServiciosSeleccionados([]);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva Factura</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                  {clientes.map((cliente) => (
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
                onValueChange={(value) => form.setValue("metodoPago", value)}
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
                  {servicios
                    .filter(
                      (s) => !serviciosSeleccionados.find((ss) => ss.id === s.id)
                    )
                    .map((servicio) => (
                      <SelectItem key={servicio.id} value={servicio.id.toString()}>
                        {servicio.nombre} - ${servicio.precio.toFixed(2)}
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
            <Button type="submit">Crear Factura</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
