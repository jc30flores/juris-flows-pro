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

const usuarioSchema = z
  .object({
    nombre: z
      .string()
      .min(1, "El nombre es requerido")
      .max(100, "El nombre debe tener máximo 100 caracteres"),
    email: z.string().email("El correo no es válido"),
    rol: z.enum(["ADMIN", "COLABORADOR", "CONTADOR"], {
      required_error: "Debe seleccionar un rol",
    }),
    pin: z
      .string()
      .min(4, "El PIN debe tener al menos 4 dígitos")
      .max(6, "El PIN debe tener máximo 6 dígitos")
      .regex(/^\d+$/, "El PIN solo debe contener números"),
    confirmarPin: z.string(),
    activo: z.boolean().default(true),
  })
  .refine((data) => data.pin === data.confirmarPin, {
    message: "Los PINs no coinciden",
    path: ["confirmarPin"],
  });

interface NuevoUsuarioModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NuevoUsuarioModal({
  open,
  onOpenChange,
}: NuevoUsuarioModalProps) {
  const form = useForm<z.infer<typeof usuarioSchema>>({
    resolver: zodResolver(usuarioSchema),
    defaultValues: {
      nombre: "",
      email: "",
      rol: "COLABORADOR",
      pin: "",
      confirmarPin: "",
      activo: true,
    },
  });

  const onSubmit = (data: z.infer<typeof usuarioSchema>) => {
    const { confirmarPin, ...userData } = data;
    console.log(userData);

    toast({
      title: "Usuario creado",
      description: "El usuario se ha creado exitosamente",
    });

    form.reset();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Usuario</DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
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
            <Label htmlFor="email">Correo Electrónico</Label>
            <Input
              id="email"
              type="email"
              placeholder="usuario@cuska.local"
              {...form.register("email")}
            />
            {form.formState.errors.email && (
              <p className="text-sm text-destructive">
                {form.formState.errors.email.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="rol">Rol</Label>
            <Select
              value={form.watch("rol")}
              onValueChange={(value) =>
                form.setValue("rol", value as any)
              }
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

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="pin">PIN (4-6 dígitos)</Label>
              <Input
                id="pin"
                type="password"
                placeholder="****"
                maxLength={6}
                {...form.register("pin")}
              />
              {form.formState.errors.pin && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.pin.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmarPin">Confirmar PIN</Label>
              <Input
                id="confirmarPin"
                type="password"
                placeholder="****"
                maxLength={6}
                {...form.register("confirmarPin")}
              />
              {form.formState.errors.confirmarPin && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.confirmarPin.message}
                </p>
              )}
            </div>
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
            >
              Cancelar
            </Button>
            <Button type="submit">Crear Usuario</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
