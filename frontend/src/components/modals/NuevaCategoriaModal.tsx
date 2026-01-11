import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { isAxiosError } from "axios";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { ServiceCategory } from "@/types/service";

const categoriaSchema = z.object({
  nombre: z.string().min(1, { message: "El nombre es requerido" }),
});

type CategoriaFormValues = z.infer<typeof categoriaSchema>;

interface NuevaCategoriaModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated?: () => void | Promise<void>;
}

export function NuevaCategoriaModal({ open, onOpenChange, onCreated }: NuevaCategoriaModalProps) {
  const form = useForm<CategoriaFormValues>({
    resolver: zodResolver(categoriaSchema),
    defaultValues: {
      nombre: "",
    },
  });
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [listError, setListError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const editInputRef = useRef<HTMLInputElement | null>(null);

  const fetchCategories = async () => {
    setLoadingCategories(true);
    setListError("");
    try {
      const response = await api.get<ServiceCategory[]>("/service-categories/");
      setCategories(response.data);
    } catch (error) {
      console.error("Error al cargar categorías", error);
      setListError("No se pudieron cargar las categorías");
    } finally {
      setLoadingCategories(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchCategories();
    } else {
      setSearchTerm("");
      setEditingId(null);
      setEditValue("");
      setSavingId(null);
      setDeletingId(null);
      setListError("");
    }
  }, [open]);

  useEffect(() => {
    if (editingId !== null) {
      editInputRef.current?.focus();
    }
  }, [editingId]);

  const filteredCategories = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return categories;
    return categories.filter((category) =>
      category.name.toLowerCase().includes(term),
    );
  }, [categories, searchTerm]);

  const onSubmit = async (data: CategoriaFormValues) => {
    const payload = {
      name: data.nombre.trim(),
    };

    try {
      setIsCreating(true);
      const response = await api.post<ServiceCategory>("/service-categories/", payload);
      toast.success("Categoría creada exitosamente");
      setCategories((prev) => [response.data, ...prev]);
      form.reset();
      if (onCreated) {
        await onCreated();
      }
      onOpenChange(false);
    } catch (error) {
      console.error("Error al crear la categoría", error);
      toast.error("No se pudo crear la categoría");
    } finally {
      setIsCreating(false);
    }
  };

  const startEditing = (category: ServiceCategory) => {
    setEditingId(category.id);
    setEditValue(category.name);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditValue("");
  };

  const handleSave = async (category: ServiceCategory) => {
    const trimmed = editValue.trim();
    if (!trimmed) {
      toast.error("El nombre es requerido");
      return;
    }
    if (trimmed === category.name) {
      cancelEditing();
      return;
    }

    try {
      setSavingId(category.id);
      const response = await api.patch<ServiceCategory>(
        `/service-categories/${category.id}/`,
        { name: trimmed },
      );
      setCategories((prev) =>
        prev.map((item) => (item.id === category.id ? response.data : item)),
      );
      toast.success("Categoría actualizada");
      cancelEditing();
    } catch (error) {
      console.error("Error al actualizar la categoría", error);
      toast.error("No se pudo actualizar la categoría");
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (category: ServiceCategory) => {
    const confirmed = window.confirm(
      `¿Eliminar la categoría "${category.name}"? Esta acción no se puede deshacer.`,
    );
    if (!confirmed) return;

    try {
      setDeletingId(category.id);
      await api.delete(`/service-categories/${category.id}/`);
      setCategories((prev) => prev.filter((item) => item.id !== category.id));
      toast.success("Categoría eliminada");
      if (onCreated) {
        await onCreated();
      }
    } catch (error) {
      console.error("Error al eliminar la categoría", error);
      let message = "No se pudo eliminar la categoría";
      if (isAxiosError(error)) {
        const detail =
          typeof error.response?.data?.detail === "string"
            ? error.response?.data?.detail.toLowerCase()
            : "";
        if (detail.includes("protect") || detail.includes("foreign key")) {
          message =
            "No se puede eliminar porque está en uso. Primero reasigna o elimina los productos asociados.";
        }
      }
      toast.error(message);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Nueva Categoría</DialogTitle>
        </DialogHeader>
        <div className="space-y-6">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold">Crear nueva categoría</h3>
              </div>
              <FormField
                control={form.control}
                name="nombre"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nombre de la Categoría</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Ingrese el nombre de la categoría"
                        className="shadow-inner"
                        {...field}
                        onChange={(event) =>
                          field.onChange(event.target.value.toUpperCase())
                        }
                        value={field.value}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancelar
                </Button>
                <Button type="submit" disabled={isCreating}>
                  {isCreating ? "Guardando..." : "Crear Categoría"}
                </Button>
              </DialogFooter>
            </form>
          </Form>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Categorías existentes</h3>
            </div>
            <Input
              placeholder="Buscar categoría..."
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              className="shadow-inner"
            />
            <div className="rounded-md border border-border bg-muted/10 max-h-[60vh] overflow-y-auto">
              {loadingCategories && (
                <div className="p-4 text-sm text-muted-foreground">
                  Cargando categorías...
                </div>
              )}
              {listError && !loadingCategories && (
                <div className="p-4 text-sm text-destructive">{listError}</div>
              )}
              {!loadingCategories && !listError && (
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 sticky top-0">
                    <tr className="border-b border-border">
                      <th className="px-4 py-2 text-left font-medium">Nombre</th>
                      <th className="px-4 py-2 text-right font-medium">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCategories.map((category) => {
                      const isEditing = editingId === category.id;
                      const isSaving = savingId === category.id;
                      const isDeleting = deletingId === category.id;
                      return (
                        <tr
                          key={category.id}
                          className="border-b border-border last:border-b-0"
                        >
                          <td className="px-4 py-2">
                            {isEditing ? (
                              <Input
                                ref={editInputRef}
                                value={editValue}
                                onChange={(event) =>
                                  setEditValue(event.target.value.toUpperCase())
                                }
                                onKeyDown={(event) => {
                                  if (event.key === "Enter") {
                                    event.preventDefault();
                                    handleSave(category);
                                  }
                                  if (event.key === "Escape") {
                                    event.preventDefault();
                                    cancelEditing();
                                  }
                                }}
                                className="shadow-inner"
                                disabled={isSaving}
                              />
                            ) : (
                              <span className="font-medium">{category.name}</span>
                            )}
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex justify-end gap-2">
                              {isEditing ? (
                                <>
                                  <Button
                                    size="sm"
                                    onClick={() => handleSave(category)}
                                    disabled={isSaving}
                                  >
                                    {isSaving ? "Guardando..." : "Guardar"}
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={cancelEditing}
                                    disabled={isSaving}
                                  >
                                    Cancelar
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => startEditing(category)}
                                    disabled={isDeleting || isCreating}
                                  >
                                    Editar
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    onClick={() => handleDelete(category)}
                                    disabled={isDeleting || isCreating}
                                  >
                                    {isDeleting ? "Eliminando..." : "Eliminar"}
                                  </Button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredCategories.length === 0 && (
                      <tr>
                        <td
                          className="px-4 py-4 text-sm text-muted-foreground"
                          colSpan={2}
                        >
                          No hay categorías creadas todavía.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
