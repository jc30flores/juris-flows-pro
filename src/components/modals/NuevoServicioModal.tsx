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
import { Switch } from "@/components/ui/switch";
import { toast } from "@/hooks/use-toast";

const servicioSchema = z.object({
  codigo: z
    .string()
    .min(1, "El código es requerido")
    .max(20, "El código debe tener máximo 20 caracteres"),
  nombre: z
    .string()
    .min(1, "El nombre es requerido")
    .max(200, "El nombre debe tener máximo 200 caracteres"),
  categoria: z.string().min(1, "La categoría es requerida"),
  precioBase: z
    .string()
    .min(1, "El precio es requerido")
    .refine((val) => !isNaN(Number(val)) && Number(val) > 0, {
      message: "El precio debe ser mayor a 0",
    }),
  activo: z.boolean().default(true),
});

interface NuevoServicioModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevoServicioModal({
  open,
  onOpenChange,
}: NuevoServicioModalProps) {
  const form = useForm<z.infer<typeof servicioSchema>>({
    resolver: zodResolver(servicioSchema),
    defaultValues: {
      codigo: "",
      nombre: "",
      categoria: "",
      precioBase: "",
      activo: true,
    },
  });

  const categorias = [
    "Compra Venta",
    "Escrituras Públicas",
    "Autenticaciones",
    "Certificaciones",
    "Poderes",
    "Arrendamientos",
    "Testamentos",
    "Otros",
  ];

  const onSubmit = (data: z.infer<typeof servicioSchema>) => {
    console.log({
      ...data,
      precioBase: Number(data.precioBase),
    });

    toast({
      title: "Servicio creado",
      description: "El servicio se ha creado exitosamente",
    });

    form.reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Servicio</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="codigo">Código</Label>
            <Input
              id="codigo"
              placeholder="SRV-001"
              {...form.register("codigo")}
            />
            {form.formState.errors.codigo && (
              <p className="text-sm text-destructive">
                {form.formState.errors.codigo.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre del Servicio</Label>
            <Input
              id="nombre"
              placeholder="Compra Venta de Vehículos"
              {...form.register("nombre")}
            />
            {form.formState.errors.nombre && (
              <p className="text-sm text-destructive">
                {form.formState.errors.nombre.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="categoria">Categoría</Label>
            <Select
              value={form.watch("categoria")}
              onValueChange={(value) => form.setValue("categoria", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar categoría" />
              </SelectTrigger>
              <SelectContent>
                {categorias.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.categoria && (
              <p className="text-sm text-destructive">
                {form.formState.errors.categoria.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="precioBase">Precio Base</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="precioBase"
                type="number"
                step="0.01"
                placeholder="0.00"
                className="pl-7"
                {...form.register("precioBase")}
              />
            </div>
            {form.formState.errors.precioBase && (
              <p className="text-sm text-destructive">
                {form.formState.errors.precioBase.message}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="activo"
              checked={form.watch("activo")}
              onCheckedChange={(checked) => form.setValue("activo", checked)}
            />
            <Label htmlFor="activo" className="cursor-pointer">
              Servicio Activo
            </Label>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit">Crear Servicio</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
