import { isValid, parse, parseISO } from "date-fns";

const EL_SALVADOR_TZ = "America/El_Salvador";

type DateParts = {
  year: number;
  month: number;
  day: number;
};

export const getElSalvadorDateParts = (date: Date): DateParts => {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: EL_SALVADOR_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });

  const parts = formatter.formatToParts(date);
  const year = Number(parts.find((part) => part.type === "year")?.value ?? "0");
  const month = Number(parts.find((part) => part.type === "month")?.value ?? "0");
  const day = Number(parts.find((part) => part.type === "day")?.value ?? "0");

  return { year, month, day };
};

export const toElSalvadorMidnightUtc = (date: Date): Date => {
  const { year, month, day } = getElSalvadorDateParts(date);
  return new Date(Date.UTC(year, month - 1, day));
};

export const formatDateInElSalvador = (date: Date): string => {
  const formatter = new Intl.DateTimeFormat("es-SV", {
    timeZone: EL_SALVADOR_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(date);
};

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
