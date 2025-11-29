import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

interface VerGastoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gasto: any;
}

export function VerGastoModal({
  open,
  onOpenChange,
  gasto,
}: VerGastoModalProps) {
  if (!gasto) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Detalle del Gasto</DialogTitle>
          <DialogDescription>
            Información completa del gasto
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Nombre</p>
              <p className="font-medium">{gasto.nombre}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Proveedor</p>
              <p className="font-medium">{gasto.proveedor}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Fecha</p>
              <p className="font-medium">{gasto.fecha}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Total</p>
              <p className="font-bold text-lg text-primary">
                ${gasto.total.toFixed(2)}
              </p>
            </div>
          </div>

          {gasto.descripcion && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Descripción</p>
              <p className="font-medium">{gasto.descripcion}</p>
            </div>
          )}

          <div className="flex justify-end pt-4">
            <Button onClick={() => onOpenChange(false)}>Cerrar</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
