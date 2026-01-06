import { describe, expect, it } from "vitest";
import {
  formatDateInElSalvador,
  parseInvoiceDate,
  toElSalvadorMidnightUtc,
} from "./dates";

describe("parseInvoiceDate", () => {
  it("parses ISO date", () => {
    const parsed = parseInvoiceDate("2026-01-05");
    expect(parsed).not.toBeNull();
    expect(parsed?.getFullYear()).toBe(2026);
    expect(parsed?.getMonth()).toBe(0);
    expect(parsed?.getDate()).toBe(5);
  });

  it("parses ISO datetime", () => {
    const parsed = parseInvoiceDate("2026-01-05T10:00:00Z");
    expect(parsed).not.toBeNull();
  });

  it("parses DD/MM/YYYY", () => {
    const parsed = parseInvoiceDate("05/01/2026");
    expect(parsed).not.toBeNull();
    expect(parsed?.getMonth()).toBe(0);
    expect(parsed?.getDate()).toBe(5);
  });

  it("returns null for empty input", () => {
    expect(parseInvoiceDate("")).toBeNull();
    expect(parseInvoiceDate(null)).toBeNull();
  });

  it("formats El Salvador dates without day rollover at 10pm ES", () => {
    const tenPmEs = new Date("2026-01-06T04:00:00Z");
    expect(formatDateInElSalvador(tenPmEs)).toBe("05/01/2026");
  });

  it("normalizes to El Salvador midnight in UTC", () => {
    const sample = new Date("2026-01-06T04:00:00Z");
    const normalized = toElSalvadorMidnightUtc(sample);
    expect(normalized.toISOString().startsWith("2026-01-05")).toBe(true);
  });
});
