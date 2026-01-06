import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Service } from "@/types/service";
import { SelectedServicePayload } from "@/types/invoice";
import { renderCellValue } from "@/lib/render";

interface ServiceSelectorModalProps {
  open: boolean;
  services: Service[];
  onCancel: () => void;
  onConfirm: (services: SelectedServicePayload[]) => void;
  initialSelected?: SelectedServicePayload[];
}

export function ServiceSelectorModal({
  open,
  services,
  onCancel,
  onConfirm,
  initialSelected = [],
}: ServiceSelectorModalProps) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<SelectedServicePayload[]>([]);

  useEffect(() => {
    if (open) {
      setSelected(initialSelected);
      setSearch("");
    }
  }, [initialSelected, open]);

  const filteredServices = useMemo(() => {
    const term = search.toLowerCase().trim();
    if (!term) return services;
    return services.filter((service) => {
      const haystack = `${service.name} ${service.code}`.toLowerCase();
      return haystack.includes(term);
    });
  }, [search, services]);

  const updateQuantity = (service: Service, delta: number) => {
    setSelected((prev) => {
      const existingIndex = prev.findIndex((item) => item.service_id === service.id);
      if (existingIndex !== -1) {
        const updated = [...prev];
        const current = updated[existingIndex];
        const quantity = current.quantity + delta;
        if (quantity <= 0) {
          return updated.filter((_, idx) => idx !== existingIndex);
        }
        const price = Number(current.price || service.base_price || 0);
        updated[existingIndex] = {
          ...current,
          quantity,
          subtotal: Number((price * quantity).toFixed(2)),
        };
        return updated;
      }

      if (delta < 0) return prev;

      const price = Number(service.base_price || 0);
      return [
        ...prev,
        {
          service_id: service.id,
          name: service.name,
          price,
          quantity: 1,
          subtotal: Number(price.toFixed(2)),
        },
      ];
    });
  };

  const subtotal = useMemo(
    () => selected.reduce((acc, item) => acc + Number(item.subtotal || 0), 0),
    [selected],
  );

  const handleConfirm = () => {
    onConfirm(selected);
  };

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onCancel()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Seleccionar Servicios</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="searchService">Buscar servicio por nombre o texto</Label>
            <Input
              id="searchService"
              placeholder="Buscar servicio por nombre o texto"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && filteredServices.length > 0) {
                  e.preventDefault();
                  updateQuantity(filteredServices[0], 1);
                  setSearch("");
                }
              }}
            />
          </div>

          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Resultados</p>
            <div className="max-h-64 overflow-y-auto rounded-lg border border-border">
              {filteredServices.length > 0 ? (
                <ul className="divide-y divide-border">
                  {filteredServices.map((service) => (
                    <li
                      key={service.id}
                      className="flex flex-wrap items-center gap-2 px-4 py-3 text-sm sm:text-base"
                    >
                      <div className="flex-1 min-w-0 text-left">
                        <p className="font-medium leading-tight truncate">
                          {service.name} · ${Number(service.base_price || 0).toFixed(2)} · {service.code || "-"}
                        </p>
                      </div>
                      <div className="inline-flex items-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => updateQuantity(service, -1)}
                        >
                          -
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => updateQuantity(service, 1)}
                        >
                          +
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="p-4 text-sm text-muted-foreground">
                  No se encontraron servicios
                </div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold">Servicios seleccionados</p>
              <span className="text-sm text-muted-foreground">
                Total: ${subtotal.toFixed(2)}
              </span>
            </div>

            {selected.length > 0 ? (
              <div className="space-y-3">
                <div className="hidden sm:block overflow-x-auto rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">Servicio</th>
                        <th className="px-4 py-3 text-center font-medium">Cantidad</th>
                        <th className="px-4 py-3 text-right font-medium">Subtotal</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selected.map((item) => (
                        <tr key={item.service_id} className="border-t border-border">
                          <td className="px-4 py-3">
                            <p className="font-medium leading-tight">{item.name}</p>
                            <p className="text-xs text-muted-foreground">
                              ID: {renderCellValue(item.service_id)}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-center">{item.quantity}</td>
                          <td className="px-4 py-3 text-right font-semibold">
                            ${Number(item.subtotal).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="grid gap-3 sm:hidden">
                  {selected.map((item) => (
                    <div
                      key={item.service_id}
                      className="rounded-lg border border-border p-3 space-y-1"
                    >
                      <p className="text-sm font-medium leading-tight">{item.name}</p>
                      <p className="text-xs text-muted-foreground">
                        ID: {renderCellValue(item.service_id)}
                      </p>
                      <div className="flex items-center justify-between text-sm">
                        <span>Cantidad:</span>
                        <span className="font-medium">{item.quantity}</span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span>Subtotal:</span>
                        <span className="font-semibold">${Number(item.subtotal).toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No hay servicios seleccionados.</p>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" type="button" onClick={onCancel}>
            Cancelar
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={selected.length === 0}>
            Confirmar selección
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
