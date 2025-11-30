import { useEffect, useMemo, useState } from "react";
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
import { toast } from "@/hooks/use-toast";
import { Client, ClientPayload } from "@/types/client";
import { useGeoData } from "@/hooks/useGeoData";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from "@/components/ui/command";

const normalizeText = (value: string): string => {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, "")
    .replace(/\s+/g, " ")
    .trim();
};

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
  cliente: Client | null;
  onSubmit: (payload: Partial<ClientPayload>) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function EditarClienteModal({
  open,
  onOpenChange,
  cliente,
  onSubmit,
  onDelete,
}: EditarClienteModalProps) {
  const [tipoFiscal, setTipoFiscal] = useState<"CF" | "CCF" | "SX">("CF");
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { departments, getMunicipalitiesByDept, activities, loading } = useGeoData();
  const [departmentCode, setDepartmentCode] = useState("");
  const [municipalityCode, setMunicipalityCode] = useState("");
  const [activityCode, setActivityCode] = useState("");
  const [activitySearch, setActivitySearch] = useState("");
  const [openDept, setOpenDept] = useState(false);
  const [openMunicipality, setOpenMunicipality] = useState(false);
  const [openActivity, setOpenActivity] = useState(false);

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

  const municipalitiesByDept = useMemo(
    () =>
      getMunicipalitiesByDept(departmentCode).sort((a, b) =>
        a.name.localeCompare(b.name),
      ),
    [departmentCode, getMunicipalitiesByDept],
  );

  const selectedDepartment = useMemo(
    () => departments.find((dept) => dept.code === departmentCode),
    [departments, departmentCode],
  );

  const selectedMunicipality = useMemo(
    () =>
      municipalitiesByDept.find((municipality) => municipality.muni_code === municipalityCode),
    [municipalitiesByDept, municipalityCode],
  );

  const selectedActivity = useMemo(
    () => activities.find((activity) => activity.code === activityCode),
    [activities, activityCode],
  );

  const filteredActivities = useMemo(() => {
    const searchQuery = normalizeText(activitySearch || "");

    const filteredActivities = activities.filter((activity) => {
      const target = normalizeText(`${activity.description} ${activity.code}`);
      if (!searchQuery) return true;
      return target.includes(searchQuery);
    });

    return filteredActivities;
  }, [activitySearch, activities]);

  const visibleActivities = useMemo(
    () => filteredActivities.slice(0, 7),
    [filteredActivities],
  );

  useEffect(() => {
    if (cliente && open) {
      setTipoFiscal(cliente.client_type);
      setDepartmentCode(cliente.department_code || "");
      setMunicipalityCode(cliente.municipality_code || "");
      setActivityCode(cliente.activity_code || "");
      form.reset({
        nombre: cliente.full_name || "",
        telefono: cliente.phone || "",
        correo: cliente.email || "",
        tipoFiscal: cliente.client_type || "CF",
        dui: cliente.dui || "",
        nombreComercial: cliente.company_name || "",
        nit: cliente.nit || "",
        nrc: cliente.nrc || "",
        giro: cliente.giro || "",
        direccion: cliente.direccion || "",
      });
    }
  }, [cliente, open, form]);

  const handleSubmit = async (values: z.infer<typeof clienteSchemaBase>) => {
    const payload: Partial<ClientPayload> = {
      full_name: values.nombre,
      company_name: values.nombreComercial || undefined,
      client_type: values.tipoFiscal,
      dui: values.dui || undefined,
      nit: values.nit || undefined,
      phone: values.telefono || undefined,
      email: values.correo || undefined,
      department_code: departmentCode || null,
      municipality_code: municipalityCode || null,
      activity_code:
        ["CCF", "SX"].includes(values.tipoFiscal) && activityCode
          ? activityCode
          : null,
    };

    try {
      setSubmitting(true);
      await onSubmit(payload);
      toast({
        title: "Cliente actualizado",
        description: "La información del cliente se guardó correctamente",
      });
      form.reset();
      onOpenChange(false);
    } catch (error) {
      console.error("Error al actualizar cliente", error);
      toast({
        title: "Error al actualizar",
        description: "No se pudo actualizar el cliente. Intenta de nuevo.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!cliente) return;
    if (!window.confirm("¿Eliminar este cliente?")) return;

    try {
      setDeleting(true);
      await onDelete();
      toast({
        title: "Cliente eliminado",
        description: "El cliente se eliminó correctamente",
      });
      onOpenChange(false);
    } catch (error) {
      console.error("Error al eliminar cliente", error);
      toast({
        title: "Error al eliminar",
        description: "No se pudo eliminar el cliente. Intenta de nuevo.",
        variant: "destructive",
      });
    } finally {
      setDeleting(false);
    }
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
      setActivityCode("");
    } else if (newTipo === "SX") {
      form.setValue("dui", "");
      form.setValue("nombreComercial", "");
      form.setValue("nit", "");
      form.setValue("nrc", "");
      form.setValue("giro", "");
      form.setValue("direccion", "");
      setActivityCode("");
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
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
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

            <div className="space-y-2">
              <FormLabel>Departamento</FormLabel>
              <Popover open={openDept} onOpenChange={setOpenDept}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                    disabled={loading}
                  >
                    {selectedDepartment?.name ||
                      (loading ? "Cargando..." : "Selecciona un departamento")}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[320px] p-0">
                  <Command>
                    <CommandInput placeholder="Buscar departamento" />
                    <CommandEmpty>Sin resultados</CommandEmpty>
                    <CommandGroup>
                      {departments.map((dept) => (
                        <CommandItem
                          key={dept.code}
                          value={`${dept.code}-${dept.name}`}
                          onSelect={() => {
                            setDepartmentCode(dept.code);
                            setMunicipalityCode("");
                            setOpenDept(false);
                          }}
                        >
                          {dept.name}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            <div className="space-y-2">
              <FormLabel>Municipio</FormLabel>
              <Popover open={openMunicipality} onOpenChange={setOpenMunicipality}>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    className="w-full justify-between"
                    disabled={!departmentCode || loading}
                  >
                    {selectedMunicipality?.name ||
                      (!departmentCode
                        ? "Selecciona un departamento"
                        : loading
                          ? "Cargando..."
                          : "Selecciona un municipio")}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[320px] p-0">
                  <Command>
                    <CommandInput placeholder="Buscar municipio" />
                    <CommandEmpty>Sin resultados</CommandEmpty>
                    <CommandGroup>
                      {municipalitiesByDept.map((municipality) => (
                        <CommandItem
                          key={municipality.id}
                          value={`${municipality.muni_code}-${municipality.name}`}
                          onSelect={() => {
                            setMunicipalityCode(municipality.muni_code);
                            setOpenMunicipality(false);
                          }}
                        >
                          {municipality.name}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {["CCF", "SX"].includes(tipoFiscal) && (
              <div className="space-y-2 md:col-span-2">
                <FormLabel>Giro o descripción de actividad</FormLabel>
                <Popover open={openActivity} onOpenChange={setOpenActivity}>
                  <PopoverTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      role="combobox"
                      className="w-full justify-between"
                      disabled={loading}
                    >
                      {selectedActivity
                        ? `${selectedActivity.description} (${selectedActivity.code})`
                        : loading
                          ? "Cargando..."
                          : "Selecciona una actividad"}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[420px] p-0">
                    <Command>
                      <CommandInput
                        placeholder="Buscar actividad"
                        value={activitySearch}
                        onValueChange={setActivitySearch}
                      />
                      <CommandEmpty>Sin resultados</CommandEmpty>
                      <CommandGroup>
                        {visibleActivities.map((activity) => (
                          <CommandItem
                            key={activity.code}
                            value={`${activity.code}-${activity.description}`}
                            onSelect={() => {
                              setActivityCode(activity.code);
                              setOpenActivity(false);
                            }}
                          >
                            {activity.description} ({activity.code})
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
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
              <Button
                type="button"
                variant="destructive"
                className="flex-1"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? "Eliminando..." : "Eliminar"}
              </Button>
              <Button type="submit" className="flex-1" disabled={submitting}>
                {submitting ? "Guardando..." : "Guardar Cambios"}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
