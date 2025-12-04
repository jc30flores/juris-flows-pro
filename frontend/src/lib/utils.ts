import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getLocalDateISO(dateValue: Date = new Date()) {
  const localizedDate = new Date(
    dateValue.getTime() - dateValue.getTimezoneOffset() * 60000,
  );
  return localizedDate.toISOString().split("T")[0];
}

export function parseLocalDate(value: string | Date) {
  if (value instanceof Date) {
    return new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }

  return new Date(`${value}T00:00:00`);
}
