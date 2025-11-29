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
import { useMemo, useState } from "react";
import { ClientPayload } from "@/types/client";

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
    .min(1, "El teléfono es requerido"),
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
    .regex(/^\d{1,14}$/, "Ingrese solo dígitos (máximo 14)"),
  nrc: z
    .string()
    .min(1, "El NRC es requerido para CCF")
    .regex(/^\d{7,8}$/, "Ingrese 7 u 8 dígitos"),
});

const clienteSXSchema = clienteSchemaBase;

const PHONE_LENGTHS: Record<string, number> = {
  "+503": 8,
  "+1": 10,
};

const getMaxPhoneDigits = (countryCode: string) => {
  return PHONE_LENGTHS[countryCode] ?? 15;
};

const formatPhoneNumber = (countryCode: string, digits: string) => {
  if (!digits) return "";

  if (countryCode === "+503") {
    const partA = digits.slice(0, 4);
    const partB = digits.slice(4, 8);
    return partB ? `${partA}-${partB}` : partA;
  }

  if (countryCode === "+1") {
    const area = digits.slice(0, 3);
    const first = digits.slice(3, 6);
    const last = digits.slice(6, 10);

    if (digits.length <= 3) return area ? `(${area}` : "";
    if (digits.length <= 6) return `(${area}) ${first}`;
    return `(${area}) ${first}-${last}`;
  }

  return digits;
};

interface NuevoClienteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: ClientPayload) => Promise<void>;
}

export function NuevoClienteModal({
  open,
  onOpenChange,
  onSubmit,
}: NuevoClienteModalProps) {
  const [tipoFiscal, setTipoFiscal] = useState<"CF" | "CCF" | "SX">("CF");
  const [submitting, setSubmitting] = useState(false);
  const [countryCode, setCountryCode] = useState("+503");
  const [phoneDigits, setPhoneDigits] = useState("");

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

  const resolver = useMemo(() => zodResolver(getSchema()), [tipoFiscal]);

  const form = useForm<any>({
    resolver,
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

  const syncPhoneValue = (
    digits: string,
    currentCountryCode: string,
    applyFormatting: boolean,
  ) => {
    const maxDigits = applyFormatting ? getMaxPhoneDigits(currentCountryCode) : 15;
    const trimmed = digits.slice(0, maxDigits);
    const formatted = applyFormatting
      ? formatPhoneNumber(currentCountryCode, trimmed)
      : trimmed;
    const phoneValue = trimmed ? `${currentCountryCode} ${formatted}` : "";
    setPhoneDigits(trimmed);
    form.setValue("telefono", phoneValue, { shouldValidate: true });
  };

  const handleSubmit = async (data: any) => {
    const payload: ClientPayload = {
      full_name: data.nombre,
      company_name: data.nombreComercial || undefined,
      client_type: data.tipoFiscal,
      dui: data.dui || undefined,
      nit: data.nit || undefined,
      phone: data.telefono || undefined,
      email: data.correo || undefined,
    };

    try {
      setSubmitting(true);
      await onSubmit(payload);
      toast({
        title: "Cliente creado",
        description: "El cliente se ha creado exitosamente",
      });
      form.reset();
      setPhoneDigits("");
      setCountryCode("+503");
      onOpenChange(false);
    } catch (error) {
      console.error("Error al crear cliente", error);
      toast({
        title: "Error al crear cliente",
        description: "No se pudo guardar el cliente. Intenta de nuevo.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleTipoFiscalChange = (value: "CF" | "CCF" | "SX") => {
    setTipoFiscal(value);
    form.setValue("tipoFiscal", value);
    // Limpiar campos específicos al cambiar tipo
    form.setValue("dui", "");
    form.setValue("nit", "");
    form.setValue("nrc", "");
    form.setValue("nombreComercial", "");
    setPhoneDigits("");
    setCountryCode("+503");
    syncPhoneValue("", "+503", ["CF", "CCF"].includes(value));
  };

  const handleDuiChange = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 9);
    const formatted = digits.length > 8 ? `${digits.slice(0, 8)}-${digits.slice(8)}` : digits;
    form.setValue("dui", formatted, { shouldValidate: true });
  };

  const handleNitChange = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 14);
    form.setValue("nit", digits, { shouldValidate: true });
  };

  const handleNrcChange = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 8);
    form.setValue("nrc", digits, { shouldValidate: true });
  };

  const handleCountryCodeChange = (value: string) => {
    setCountryCode(value);
    syncPhoneValue(
      phoneDigits,
      value,
      ["CF", "CCF"].includes(tipoFiscal),
    );
  };

  const handlePhoneChange = (value: string) => {
    const rawDigits = value.replace(/\D/g, "");
    const shouldFormat = ["CF", "CCF"].includes(tipoFiscal);
    syncPhoneValue(rawDigits, countryCode, shouldFormat);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {tipoFiscal === "CCF" ? "Nuevo Contribuyente" : "Nuevo Cliente"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
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
                  value={form.watch("dui") || ""}
                  onChange={(event) => handleDuiChange(event.target.value)}
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
                    placeholder="00000000000000"
                    value={form.watch("nit") || ""}
                    onChange={(event) => handleNitChange(event.target.value)}
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
                    value={form.watch("nrc") || ""}
                    onChange={(event) => handleNrcChange(event.target.value)}
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
              <div className="flex gap-2">
                <Select value={countryCode} onValueChange={handleCountryCodeChange}>
                  <SelectTrigger className="w-[110px]">
                    <SelectValue placeholder="Código" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="+503">+503</SelectItem>
                    <SelectItem value="+1">+1</SelectItem>
                    <SelectItem value="+52">+52</SelectItem>
                    <SelectItem value="+34">+34</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  id="telefono"
                  placeholder={
                    countryCode === "+503"
                      ? "0000-0000"
                      : countryCode === "+1"
                        ? "(000) 000-0000"
                        : "Número"
                  }
                  value={
                    ["CF", "CCF"].includes(tipoFiscal)
                      ? formatPhoneNumber(countryCode, phoneDigits)
                      : phoneDigits
                  }
                  onChange={(event) => handlePhoneChange(event.target.value)}
                />
              </div>
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
            <Button type="submit" disabled={submitting}>
              {submitting ? "Guardando..." : "Crear Cliente"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
