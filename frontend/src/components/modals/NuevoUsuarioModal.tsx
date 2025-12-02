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
import { StaffUserPayload } from "@/types/staffUser";

const usuarioSchema = z.object({
  nombre: z
    .string()
    .min(1, "El nombre es requerido")
    .max(100, "El nombre debe tener máximo 100 caracteres"),
  usuario: z
    .string()
    .min(1, "El usuario es requerido")
    .max(150, "El usuario debe tener máximo 150 caracteres"),
  password: z
    .string()
    .min(6, "La contraseña debe tener al menos 6 caracteres"),
  rol: z.enum(["ADMIN", "COLABORADOR", "CONTADOR"], {
    required_error: "Debe seleccionar un rol",
  }),
  activo: z.boolean().default(true),
});

interface NuevoUsuarioModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: StaffUserPayload) => Promise<void>;
}

export function NuevoUsuarioModal({
  open,
  onOpenChange,
  onSubmit,
}: NuevoUsuarioModalProps) {
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<z.infer<typeof usuarioSchema>>({
    resolver: zodResolver(usuarioSchema),
    defaultValues: {
      nombre: "",
      usuario: "",
      password: "",
      rol: "COLABORADOR",
      activo: true,
    },
  });

  const handleSubmit = async (data: z.infer<typeof usuarioSchema>) => {
    const payload: StaffUserPayload = {
      full_name: data.nombre,
      username: data.usuario,
      password: data.password,
      role: data.rol,
      is_active: data.activo,
    };

    try {
      setSubmitting(true);
      await onSubmit(payload);

      toast({
        title: "Usuario creado",
        description: "El usuario se ha creado exitosamente",
      });

      form.reset();
      onOpenChange(false);
    } catch (error) {
      console.error("Error al crear usuario", error);
      toast({
        title: "Error",
        description: "No se pudo crear el usuario. Inténtalo nuevamente.",
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
          <DialogTitle>Nuevo Usuario</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="nombre">Nombre Completo</Label>
            <Input
              id="nombre"
              placeholder="Juan Alberto Pérez"
              {...form.register("nombre")}
            />
            {form.formState.errors.nombre && (
              <p className="text-sm text-destructive">
                {form.formState.errors.nombre.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="usuario">Usuario</Label>
            <Input
              id="usuario"
              placeholder="usuario.cuska"
              {...form.register("usuario")}
            />
            {form.formState.errors.usuario && (
              <p className="text-sm text-destructive">
                {form.formState.errors.usuario.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Contraseña</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••"
              {...form.register("password")}
            />
            {form.formState.errors.password && (
              <p className="text-sm text-destructive">
                {form.formState.errors.password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="rol">Rol</Label>
            <Select
              value={form.watch("rol")}
              onValueChange={(value) => form.setValue("rol", value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ADMIN">Administrador</SelectItem>
                <SelectItem value="COLABORADOR">Colaborador</SelectItem>
                <SelectItem value="CONTADOR">Contador</SelectItem>
              </SelectContent>
            </Select>
            {form.formState.errors.rol && (
              <p className="text-sm text-destructive">
                {form.formState.errors.rol.message}
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
              Usuario Activo
            </Label>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creando..." : "Crear Usuario"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
