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
        const price = Number(current.unit_price ?? current.price ?? service.base_price ?? 0);
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
          original_unit_price: price,
          unit_price: price,
          price_overridden: false,
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
      <DialogContent
        className="flex w-[95vw] max-w-md flex-col overflow-hidden rounded-2xl p-0 sm:max-w-lg md:max-w-xl max-h-[90vh]"
      >
        <DialogHeader className="sticky top-0 z-10 border-b border-border bg-background/95 px-6 py-4 backdrop-blur">
          <DialogTitle>Seleccionar Servicios</DialogTitle>
        </DialogHeader>

        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-y-auto px-6 pb-6 pt-4 max-h-[calc(90vh-140px)]">
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
              <div className="max-h-[45vh] overflow-y-auto rounded-lg border border-border">
                {filteredServices.length > 0 ? (
                  <ul className="divide-y divide-border">
                    {filteredServices.map((service) => (
                      <li
                        key={service.id}
                        className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-4 py-3 text-sm sm:text-base"
                      >
                        <div className="min-w-0 text-left">
                          <p
                            className="font-medium leading-tight"
                            style={{
                              display: "-webkit-box",
                              WebkitBoxOrient: "vertical",
                              WebkitLineClamp: 2,
                              overflow: "hidden",
                            }}
                          >
                            {service.name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            ${Number(service.base_price || 0).toFixed(2)} · {service.code || "-"}
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
                        className="space-y-2 rounded-lg border border-border p-3"
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
                <p className="text-sm text-muted-foreground">
                  No hay servicios seleccionados.
                </p>
              )}
            </div>
          </div>

          <DialogFooter className="sticky bottom-0 z-10 flex-col-reverse gap-2 border-t border-border bg-background/95 px-6 py-4 backdrop-blur sm:flex-row sm:justify-end">
            <Button
              variant="outline"
              type="button"
              onClick={onCancel}
              className="w-full sm:w-auto"
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleConfirm}
              disabled={selected.length === 0}
              className="w-full sm:w-auto"
            >
              Confirmar selección
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
