import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { format } from "date-fns";
import { CalendarIcon } from "lucide-react";
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
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { ExpensePayload } from "@/types/expense";

const gastoSchema = z.object({
  nombre: z
    .string()
    .min(1, "El nombre es requerido")
    .max(200, "El nombre debe tener máximo 200 caracteres"),
  proveedor: z
    .string()
    .min(1, "El proveedor es requerido")
    .max(200, "El proveedor debe tener máximo 200 caracteres"),
  fecha: z.date({
    required_error: "La fecha es requerida",
  }),
  total: z
    .string()
    .min(1, "El monto es requerido")
    .refine((val) => !isNaN(Number(val)) && Number(val) > 0, {
      message: "El monto debe ser mayor a 0",
    }),
});

interface NuevoGastoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ExpensePayload) => Promise<void>;
}

export function NuevoGastoModal({
  open,
  onOpenChange,
  onSubmit,
}: NuevoGastoModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<z.infer<typeof gastoSchema>>({
    resolver: zodResolver(gastoSchema),
    defaultValues: {
      nombre: "",
      proveedor: "",
      fecha: new Date(),
      total: "",
    },
  });

  const handleSubmit = async (data: z.infer<typeof gastoSchema>) => {
    setSubmitting(true);
    try {
      const payload: ExpensePayload = {
        name: data.nombre,
        provider: data.proveedor,
        date: format(data.fecha, "yyyy-MM-dd"),
        total: Number(data.total),
      };

      await onSubmit(payload);

      toast({
        title: "Gasto registrado",
        description: "El gasto se ha registrado exitosamente",
      });

      form.reset();
      onOpenChange(false);
    } catch (error) {
      console.error("Error al registrar gasto", error);
      toast({
        title: "Error",
        description: "No se pudo registrar el gasto. Inténtalo nuevamente.",
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
          <DialogTitle>Nuevo Gasto</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre del Gasto</Label>
            <Input
              id="nombre"
              placeholder="Papelería y Suministros"
              {...form.register("nombre")}
            />
            {form.formState.errors.nombre && (
              <p className="text-sm text-destructive">
                {form.formState.errors.nombre.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="proveedor">Proveedor</Label>
            <Input
              id="proveedor"
              placeholder="Librería Central"
              {...form.register("proveedor")}
            />
            {form.formState.errors.proveedor && (
              <p className="text-sm text-destructive">
                {form.formState.errors.proveedor.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Fecha</Label>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "w-full justify-start text-left font-normal",
                    !form.watch("fecha") && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {form.watch("fecha") ? (
                    format(form.watch("fecha"), "PPP")
                  ) : (
                    <span>Seleccionar fecha</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="single"
                  selected={form.watch("fecha")}
                  onSelect={(date) => form.setValue("fecha", date || new Date())}
                  initialFocus
                  className={cn("p-3 pointer-events-auto")}
                />
              </PopoverContent>
            </Popover>
            {form.formState.errors.fecha && (
              <p className="text-sm text-destructive">
                {form.formState.errors.fecha.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="total">Monto Total</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                $
              </span>
              <Input
                id="total"
                type="number"
                step="0.01"
                placeholder="0.00"
                className="pl-7"
                {...form.register("total")}
              />
            </div>
            {form.formState.errors.total && (
              <p className="text-sm text-destructive">
                {form.formState.errors.total.message}
              </p>
            )}
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
              {submitting ? "Guardando..." : "Registrar Gasto"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
