import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Expense } from "@/types/expense";

interface VerGastoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gasto: Expense | null;
  onDelete: (expense: Expense) => void;
}

export function VerGastoModal({
  open,
  onOpenChange,
  gasto,
  onDelete,
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
              <p className="font-medium">{gasto.name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Proveedor</p>
              <p className="font-medium">{gasto.provider}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Fecha</p>
              <p className="font-medium">{gasto.date}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Total</p>
              <p className="font-bold text-lg text-primary">
                ${Number(gasto.total).toFixed(2)}
              </p>
            </div>
          </div>

          <div className="flex justify-end pt-4 space-x-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onDelete(gasto);
              }}
            >
              Eliminar gasto
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
