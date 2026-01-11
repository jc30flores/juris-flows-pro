import { useEffect, useState } from "react";
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
    .min(1, "El código es requerido")
    .max(20, "El código debe tener máximo 20 caracteres"),
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

interface EditarServicioModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  servicio: Service | null;
  categories: ServiceCategory[];
  onSubmit: (
    payload: Partial<Omit<Service, "id" | "category"> & { category: number }>,
  ) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function EditarServicioModal({
  open,
  onOpenChange,
  servicio,
  categories,
  onSubmit,
  onDelete,
}: EditarServicioModalProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const resolveCategoryId = (category: Service["category"]): string => {
    if (typeof category === "object" && category !== null) {
      return category.id.toString();
    }
    return category?.toString() ?? "";
  };

  const form = useForm<z.infer<typeof servicioSchema>>({
    resolver: zodResolver(servicioSchema),
  });

  useEffect(() => {
    if (servicio) {
      form.reset({
        code: servicio.code,
        name: servicio.name,
        category: resolveCategoryId(servicio.category),
        base_price: servicio.base_price.toString(),
        activo: servicio.active,
      });
    }
  }, [servicio, form]);

  const handleSubmit = async (data: z.infer<typeof servicioSchema>) => {
    if (!servicio) return;
    setSubmitting(true);
    try {
      await onSubmit({
        code: data.code,
        name: data.name,
        category: Number(data.category),
        base_price: Number(data.base_price),
        active: data.activo,
      });

      toast({
        title: "Producto actualizado",
        description: "Los cambios se han guardado exitosamente",
      });

      onOpenChange(false);
    } catch (error) {
      console.error("Error al actualizar producto", error);
      toast({
        title: "Error",
        description: "No se pudo actualizar el producto",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await onDelete();
      toast({
        title: "Producto eliminado",
        description: "El producto se ha eliminado exitosamente",
      });
      setShowDeleteDialog(false);
      onOpenChange(false);
    } catch (error) {
      console.error("Error al eliminar producto", error);
      toast({
        title: "Error",
        description: "No se pudo eliminar el producto",
        variant: "destructive",
      });
    }
  };

  if (!servicio) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Producto</DialogTitle>
          </DialogHeader>

          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="codigo">Código</Label>
              <Input
                id="codigo"
                placeholder="SRV-001"
                className="shadow-inner"
                {...form.register("code")}
              />
              {form.formState.errors.code && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.code.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="nombre">Nombre del Producto</Label>
              <Input
                id="nombre"
                placeholder="Compra Venta de Vehículos"
                className="shadow-inner"
                {...form.register("name")}
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
                  className="pl-7 shadow-inner"
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
                Producto Activo
              </Label>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <Button
                type="button"
                variant="destructive"
                onClick={() => setShowDeleteDialog(true)}
                className="sm:mr-auto"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Eliminar
              </Button>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "Guardando..." : "Guardar Cambios"}
                </Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar producto?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. El producto "{servicio.name}"
              será eliminado permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
