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
import { useState } from "react";

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

interface Servicio {
  id: number;
  codigo: string;
  nombre: string;
  categoria: string;
  precioBase: number;
  activo: boolean;
}

interface EditarServicioModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  servicio: Servicio | null;
}

export function EditarServicioModal({
  open,
  onOpenChange,
  servicio,
}: EditarServicioModalProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const form = useForm<z.infer<typeof servicioSchema>>({
    resolver: zodResolver(servicioSchema),
    values: servicio
      ? {
          codigo: servicio.codigo,
          nombre: servicio.nombre,
          categoria: servicio.categoria,
          precioBase: servicio.precioBase.toString(),
          activo: servicio.activo,
        }
      : undefined,
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
      id: servicio?.id,
      ...data,
      precioBase: Number(data.precioBase),
    });

    toast({
      title: "Servicio actualizado",
      description: "Los cambios se han guardado exitosamente",
    });

    onOpenChange(false);
  };

  const handleDelete = () => {
    console.log("Eliminar servicio:", servicio?.id);

    toast({
      title: "Servicio eliminado",
      description: "El servicio se ha eliminado exitosamente",
    });

    setShowDeleteDialog(false);
    onOpenChange(false);
  };

  if (!servicio) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Servicio</DialogTitle>
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
                <Button type="submit">Guardar Cambios</Button>
              </div>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar servicio?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción no se puede deshacer. El servicio "{servicio.nombre}"
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
