import { useState } from "react";
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
import { Service, ServiceCategory } from "@/types/service";

const servicioSchema = z.object({
  code: z
    .string()
    .max(20, "El código debe tener máximo 20 caracteres")
    .optional()
    .or(z.literal("")),
  name: z
    .string()
    .min(1, "El nombre es requerido")
    .max(200, "El nombre debe tener máximo 200 caracteres"),
  category: z.string().min(1, "La categoría es requerida"),
  base_price: z
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
  categories: ServiceCategory[];
  services: Service[];
  onSubmit: (payload: Omit<Service, "id" | "category"> & { category: number }) =>
    Promise<void>;
}

export function NuevoServicioModal({
  open,
  onOpenChange,
  categories,
  services,
  onSubmit,
}: NuevoServicioModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<z.infer<typeof servicioSchema>>({
    resolver: zodResolver(servicioSchema),
    defaultValues: {
      code: "",
      name: "",
      category: "",
      base_price: "",
      activo: true,
    },
  });

  const generateCode = () => {
    const existingCodes = services
      .map((service) => service.code.trim().toUpperCase())
      .filter(Boolean);

    let counter = 1;
    // Incrementa hasta encontrar un correlativo libre
    while (true) {
      const candidate = `SRV-${String(counter).padStart(3, "0")}`;
      if (!existingCodes.includes(candidate)) {
        return candidate;
      }
      counter++;
    }
  };

  const handleSubmit = async (data: z.infer<typeof servicioSchema>) => {
    setSubmitting(true);
    const normalizedInputCode = data.code?.trim().toUpperCase() || "";
    const existingCodes = services
      .map((service) => service.code.trim().toUpperCase())
      .filter(Boolean);

    if (normalizedInputCode && existingCodes.includes(normalizedInputCode)) {
      setSubmitting(false);
      toast({
        title: "Código duplicado",
        description: "Ya existe un servicio con ese código.",
        variant: "destructive",
      });
      return;
    }

    const codeToUse = normalizedInputCode || generateCode();
    try {
      await onSubmit({
        code: codeToUse,
        name: data.name.toUpperCase(),
        category: Number(data.category),
        base_price: Number(data.base_price),
        active: data.activo,
      });

      toast({
        title: "Servicio creado",
        description: "El servicio se ha creado exitosamente",
      });

      form.reset();
      onOpenChange(false);
    } catch (error) {
      console.error("Error al crear servicio", error);
      toast({
        title: "Error",
        description: "No se pudo crear el servicio. Inténtalo nuevamente.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Servicio</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="codigo">Código</Label>
            <Input
              id="codigo"
              placeholder="SRV-001"
              {...form.register("code")}
            />
            {form.formState.errors.code && (
              <p className="text-sm text-destructive">
                {form.formState.errors.code.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre del Servicio</Label>
            <Input
              id="nombre"
              placeholder="Compra Venta de Vehículos"
              {...form.register("name", {
                onChange: (event) =>
                  form.setValue("name", event.target.value.toUpperCase()),
              })}
            />
            {form.formState.errors.name && (
              <p className="text-sm text-destructive">
                {form.formState.errors.name.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="categoria">Categoría</Label>
            <Select
              value={form.watch("category")}
              onValueChange={(value) => form.setValue("category", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar categoría" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id.toString()}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {form.formState.errors.category && (
              <p className="text-sm text-destructive">
                {form.formState.errors.category.message}
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
                {...form.register("base_price")}
              />
            </div>
            {form.formState.errors.base_price && (
              <p className="text-sm text-destructive">
                {form.formState.errors.base_price.message}
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
            <Button type="submit" disabled={submitting}>
              {submitting ? "Guardando..." : "Crear Servicio"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
