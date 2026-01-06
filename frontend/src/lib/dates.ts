import { isValid, parse, parseISO } from "date-fns";

export function parseInvoiceDate(raw: unknown): Date | null {
  if (!raw) return null;
  const value = String(raw).trim();
  if (!value) return null;

  if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
    const parsed = parseISO(value);
    return isValid(parsed) ? parsed : null;
  }

  if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
    const parsed = parse(value, "dd/MM/yyyy", new Date());
    return isValid(parsed) ? parsed : null;
  }

  const parsed = new Date(value);
  return isValid(parsed) ? parsed : null;
}
