import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const clienteSchemaBase = z.object({
  nombre: z.string().min(1, "El nombre es requerido"),
  telefono: z.string().min(1, "El teléfono es requerido"),
  correo: z.string().email("Correo electrónico inválido"),
  tipoFiscal: z.enum(["CF", "CCF", "SX"]),
  dui: z.string().optional(),
  nombreComercial: z.string().optional(),
  nit: z.string().optional(),
  nrc: z.string().optional(),
  giro: z.string().optional(),
  direccion: z.string().optional(),
});

interface EditarClienteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  cliente: any;
}

export function EditarClienteModal({
  open,
  onOpenChange,
  cliente,
}: EditarClienteModalProps) {
  const [tipoFiscal, setTipoFiscal] = useState<"CF" | "CCF" | "SX">("CF");

  const form = useForm<z.infer<typeof clienteSchemaBase>>({
    resolver: zodResolver(clienteSchemaBase),
    defaultValues: {
      nombre: "",
      telefono: "",
      correo: "",
      tipoFiscal: "CF",
      dui: "",
      nombreComercial: "",
      nit: "",
      nrc: "",
      giro: "",
      direccion: "",
    },
  });

  useEffect(() => {
    if (cliente && open) {
      setTipoFiscal(cliente.tipoFiscal);
      form.reset({
        nombre: cliente.nombre || "",
        telefono: cliente.telefono || "",
        correo: cliente.correo || "",
        tipoFiscal: cliente.tipoFiscal || "CF",
        dui: cliente.dui || "",
        nombreComercial: cliente.nombreComercial || "",
        nit: cliente.nit || "",
        nrc: cliente.nrc || "",
        giro: cliente.giro || "",
        direccion: cliente.direccion || "",
      });
    }
  }, [cliente, open, form]);

  const onSubmit = (values: z.infer<typeof clienteSchemaBase>) => {
    console.log(values);
    toast.success("Cliente actualizado exitosamente");
    form.reset();
    onOpenChange(false);
  };

  const handleTipoFiscalChange = (value: string) => {
    const newTipo = value as "CF" | "CCF" | "SX";
    setTipoFiscal(newTipo);
    form.setValue("tipoFiscal", newTipo);
    
    if (newTipo === "CF") {
      form.setValue("nombreComercial", "");
      form.setValue("nit", "");
      form.setValue("nrc", "");
      form.setValue("giro", "");
      form.setValue("direccion", "");
    } else if (newTipo === "SX") {
      form.setValue("dui", "");
      form.setValue("nombreComercial", "");
      form.setValue("nit", "");
      form.setValue("nrc", "");
      form.setValue("giro", "");
      form.setValue("direccion", "");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Editar Cliente</DialogTitle>
          <DialogDescription>
            Modifica la información del cliente
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="tipoFiscal"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tipo Fiscal</FormLabel>
                  <Select
                    onValueChange={handleTipoFiscalChange}
                    value={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona tipo fiscal" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="CF">Consumidor Final (CF)</SelectItem>
                      <SelectItem value="CCF">Crédito Fiscal (CCF)</SelectItem>
                      <SelectItem value="SX">Sin Comprobante (SX)</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="nombre"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {tipoFiscal === "CCF" ? "Razón Social" : "Nombre Completo"}
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="Ingresa el nombre" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {tipoFiscal === "CCF" && (
              <FormField
                control={form.control}
                name="nombreComercial"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nombre Comercial (Opcional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Nombre comercial" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {tipoFiscal === "CF" && (
              <FormField
                control={form.control}
                name="dui"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>DUI</FormLabel>
                    <FormControl>
                      <Input placeholder="00000000-0" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {tipoFiscal === "CCF" && (
              <>
                <FormField
                  control={form.control}
                  name="nit"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>NIT</FormLabel>
                      <FormControl>
                        <Input placeholder="0000-000000-000-0" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="nrc"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>NRC</FormLabel>
                      <FormControl>
                        <Input placeholder="000000-0" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="giro"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Giro</FormLabel>
                      <FormControl>
                        <Input placeholder="Actividad económica" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="direccion"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Dirección</FormLabel>
                      <FormControl>
                        <Input placeholder="Dirección completa" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}

            <FormField
              control={form.control}
              name="telefono"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Teléfono</FormLabel>
                  <FormControl>
                    <Input placeholder="0000-0000" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="correo"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Correo Electrónico</FormLabel>
                  <FormControl>
                    <Input
                      type="email"
                      placeholder="correo@ejemplo.com"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                className="flex-1"
              >
                Cancelar
              </Button>
              <Button type="submit" className="flex-1">
                Guardar Cambios
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
