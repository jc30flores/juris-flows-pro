import { useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

interface ChangeServicePriceModalProps {
  open: boolean;
  serviceName: string;
  currentPrice: number;
  cost?: number;
  onClose: () => void;
  onPriceUpdated: (newPrice: number) => void;
}

export function ChangeServicePriceModal({
  open,
  serviceName,
  currentPrice,
  cost = 0,
  onClose,
  onPriceUpdated,
}: ChangeServicePriceModalProps) {
  const [newPrice, setNewPrice] = useState<string>(currentPrice.toFixed(2));
  const [accessCode, setAccessCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (open) {
      setNewPrice(currentPrice.toFixed(2));
      setAccessCode("");
      setError("");
    }
  }, [currentPrice, open]);

  const { parsedPrice, parsedCost, profit, profitPercent } = useMemo(() => {
    const priceNumber = Number(newPrice) || 0;
    const costNumber = Number(cost) || 0;
    const profitValue = priceNumber - costNumber;
    const percentValue = costNumber > 0 ? (profitValue / costNumber) * 100 : 0;

    return {
      parsedPrice: priceNumber,
      parsedCost: costNumber,
      profit: profitValue,
      profitPercent: percentValue,
    };
  }, [cost, newPrice]);

  const handleClose = () => {
    if (!submitting) {
      onClose();
    }
  };

  const handleApply = async () => {
    setError("");
    if (parsedPrice <= 0) {
      setError("El nuevo precio debe ser mayor a 0.");
      return;
    }

    try {
      setSubmitting(true);
      const response = await api.post("/price-override/validate/", { code: accessCode });
      if (response.data?.valid) {
        onPriceUpdated(parsedPrice);
        onClose();
        toast({ title: "Precio actualizado", description: "El precio se actualizó correctamente." });
      } else {
        setError("Código de acceso incorrecto.");
        toast({
          title: "Código incorrecto",
          description: "Código de acceso incorrecto",
          variant: "destructive",
        });
      }
    } catch (err: unknown) {
      console.error("Error validando código de acceso", err);
      setError("No se pudo validar el código de acceso.");
      toast({
        title: "No se pudo validar el código",
        description: "Intente nuevamente.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => !value && handleClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Cambiar precio</DialogTitle>
          <p className="text-sm text-muted-foreground">{serviceName}</p>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Precio actual</Label>
              <Input value={`$${currentPrice.toFixed(2)}`} readOnly />
            </div>
            <div className="space-y-2">
              <Label>Costo</Label>
              <Input value={`$${parsedCost.toFixed(2)}`} readOnly />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="newPrice">Nuevo precio</Label>
              <Input
                id="newPrice"
                type="number"
                step="0.01"
                value={newPrice}
                onChange={(e) => setNewPrice(e.target.value)}
                min="0"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="accessCode">Código de acceso</Label>
              <Input
                id="accessCode"
                type="password"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 text-sm">
            <p className="font-medium">
              Utilidad: ${profit.toFixed(2)} ({profitPercent.toFixed(2)}%)
            </p>
            {parsedPrice < parsedCost && <Badge variant="destructive">Precio bajo costo</Badge>}
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" type="button" onClick={handleClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="button" onClick={handleApply} disabled={submitting}>
            Aplicar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
