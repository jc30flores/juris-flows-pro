import {
  endOfMonth,
  endOfWeek,
  format,
  isValid,
  parse,
  startOfMonth,
  startOfWeek,
} from "date-fns";

const EL_SALVADOR_TZ = "America/El_Salvador";
const INVOICE_DATE_FORMAT = "yyyy-MM-dd";
const INVOICE_DISPLAY_FORMAT = "dd/MM/yyyy";

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

const padDatePart = (value: number): string => String(value).padStart(2, "0");

export const getElSalvadorDateString = (date: Date = new Date()): string => {
  const { year, month, day } = getElSalvadorDateParts(date);
  return `${year}-${padDatePart(month)}-${padDatePart(day)}`;
};

const normalizeInvoiceDateString = (raw: unknown): string | null => {
  if (!raw) return null;
  const value = String(raw).trim();
  if (!value) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  return null;
};

const parseInvoiceDateString = (value: string): Date | null => {
  const parsed = parse(value, INVOICE_DATE_FORMAT, new Date());
  return isValid(parsed) ? parsed : null;
};

const getInvoiceDateRange = (
  filter: InvoiceDateFilter,
  referenceDate: Date,
): { start: string; end: string } | null => {
  if (filter === "all") return null;
  const todayEs = getElSalvadorDateString(referenceDate);
  const baseDate = parseInvoiceDateString(todayEs);
  if (!baseDate) return null;

  if (filter === "today") {
    return { start: todayEs, end: todayEs };
  }

  if (filter === "week" || filter === "this-week") {
    const start = startOfWeek(baseDate, { weekStartsOn: 1 });
    const end = endOfWeek(baseDate, { weekStartsOn: 1 });
    return {
      start: format(start, INVOICE_DATE_FORMAT),
      end: format(end, INVOICE_DATE_FORMAT),
    };
  }

  if (filter === "month" || filter === "this-month") {
    const start = startOfMonth(baseDate);
    const end = endOfMonth(baseDate);
    return {
      start: format(start, INVOICE_DATE_FORMAT),
      end: format(end, INVOICE_DATE_FORMAT),
    };
  }

  return null;
};

export type InvoiceDateFilter =
  | "all"
  | "today"
  | "week"
  | "month"
  | "this-week"
  | "this-month";

export type InvoiceDateSource = {
  issue_date?: string | null;
  date?: string | null;
};

export type InvoiceDateInfo = {
  dateString: string | null;
  formatted: string | null;
  matchesFilter: (filter: InvoiceDateFilter, referenceDate?: Date) => boolean;
};

export const getInvoiceDateInfo = (invoice: InvoiceDateSource): InvoiceDateInfo => {
  const dateString = normalizeInvoiceDateString(invoice.issue_date ?? invoice.date);
  const parsed = dateString ? parseInvoiceDateString(dateString) : null;
  const formatted = parsed ? format(parsed, INVOICE_DISPLAY_FORMAT) : null;

  const matchesFilter = (
    filter: InvoiceDateFilter,
    referenceDate: Date = new Date(),
  ): boolean => {
    if (filter === "all") return true;
    if (!dateString) return false;
    const range = getInvoiceDateRange(filter, referenceDate);
    if (!range) return false;
    return dateString >= range.start && dateString <= range.end;
  };

  return { dateString, formatted, matchesFilter };
};
