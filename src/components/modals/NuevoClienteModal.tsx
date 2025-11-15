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
import { useState } from "react";

const clienteSchemaBase = z.object({
  tipoFiscal: z.enum(["CF", "CCF", "SX"], {
    required_error: "Debe seleccionar un tipo fiscal",
  }),
  nombre: z
    .string()
    .min(1, "El nombre es requerido")
    .max(200, "El nombre debe tener máximo 200 caracteres"),
  telefono: z
    .string()
    .min(1, "El teléfono es requerido")
    .regex(/^\d{4}-\d{4}$/, "El formato debe ser 0000-0000"),
  correo: z.string().email("El correo no es válido").optional().or(z.literal("")),
});

const clienteCFSchema = clienteSchemaBase.extend({
  dui: z
    .string()
    .min(1, "El DUI es requerido para CF")
    .regex(/^\d{8}-\d$/, "El formato debe ser 00000000-0"),
});

const clienteCCFSchema = clienteSchemaBase.extend({
  nombreComercial: z.string().optional(),
  nit: z
    .string()
    .min(1, "El NIT es requerido para CCF")
    .regex(/^\d{4}-\d{6}-\d{3}-\d$/, "El formato debe ser 0000-000000-000-0"),
  nrc: z
    .string()
    .min(1, "El NRC es requerido para CCF")
    .regex(/^\d{6,8}-?\d?$/, "El NRC debe tener entre 6 y 9 dígitos"),
});

const clienteSXSchema = clienteSchemaBase;

interface NuevoClienteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevoClienteModal({
  open,
  onOpenChange,
}: NuevoClienteModalProps) {
  const [tipoFiscal, setTipoFiscal] = useState<"CF" | "CCF" | "SX">("CF");

  const getSchema = () => {
    switch (tipoFiscal) {
      case "CF":
        return clienteCFSchema;
      case "CCF":
        return clienteCCFSchema;
      case "SX":
        return clienteSXSchema;
      default:
        return clienteSchemaBase;
    }
  };

  const form = useForm<any>({
    resolver: zodResolver(getSchema()),
    defaultValues: {
      tipoFiscal: "CF",
      nombre: "",
      nombreComercial: "",
      dui: "",
      nit: "",
      nrc: "",
      telefono: "",
      correo: "",
    },
  });

  const onSubmit = (data: any) => {
    console.log(data);

    toast({
      title: "Cliente creado",
      description: "El cliente se ha creado exitosamente",
    });

    form.reset();
    onOpenChange(false);
  };

  const handleTipoFiscalChange = (value: "CF" | "CCF" | "SX") => {
    setTipoFiscal(value);
    form.setValue("tipoFiscal", value);
    // Limpiar campos específicos al cambiar tipo
    form.setValue("dui", "");
    form.setValue("nit", "");
    form.setValue("nrc", "");
    form.setValue("nombreComercial", "");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nuevo Cliente</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="tipoFiscal">Tipo Fiscal</Label>
            <Select value={tipoFiscal} onValueChange={handleTipoFiscalChange}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="CF">Consumidor Final (CF)</SelectItem>
                <SelectItem value="CCF">Crédito Fiscal (CCF)</SelectItem>
                <SelectItem value="SX">Sujeto Excluido (SX)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="nombre">
                {tipoFiscal === "CCF" ? "Razón Social" : "Nombre Completo"}
              </Label>
              <Input
                id="nombre"
                placeholder={
                  tipoFiscal === "CCF"
                    ? "Empresa S.A. de C.V."
                    : "Juan Alberto Pérez"
                }
                {...form.register("nombre")}
              />
              {form.formState.errors.nombre && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.nombre.message as string}
                </p>
              )}
            </div>

            {tipoFiscal === "CCF" && (
              <div className="space-y-2">
                <Label htmlFor="nombreComercial">Nombre Comercial (Opcional)</Label>
                <Input
                  id="nombreComercial"
                  placeholder="ABC Corp"
                  {...form.register("nombreComercial")}
                />
              </div>
            )}

            {tipoFiscal === "CF" && (
              <div className="space-y-2">
                <Label htmlFor="dui">DUI</Label>
                <Input
                  id="dui"
                  placeholder="00000000-0"
                  {...form.register("dui")}
                />
                {form.formState.errors.dui && (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.dui.message as string}
                  </p>
                )}
              </div>
            )}

            {tipoFiscal === "CCF" && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="nit">NIT</Label>
                  <Input
                    id="nit"
                    placeholder="0000-000000-000-0"
                    {...form.register("nit")}
                  />
                  {form.formState.errors.nit && (
                    <p className="text-sm text-destructive">
                      {form.formState.errors.nit.message as string}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="nrc">NRC</Label>
                  <Input
                    id="nrc"
                    placeholder="000000-0"
                    {...form.register("nrc")}
                  />
                  {form.formState.errors.nrc && (
                    <p className="text-sm text-destructive">
                      {form.formState.errors.nrc.message as string}
                    </p>
                  )}
                </div>
              </>
            )}

            <div className="space-y-2">
              <Label htmlFor="telefono">Teléfono</Label>
              <Input
                id="telefono"
                placeholder="0000-0000"
                {...form.register("telefono")}
              />
              {form.formState.errors.telefono && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.telefono.message as string}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="correo">Correo Electrónico (Opcional)</Label>
              <Input
                id="correo"
                type="email"
                placeholder="cliente@email.com"
                {...form.register("correo")}
              />
              {form.formState.errors.correo && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.correo.message as string}
                </p>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit">Crear Cliente</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
