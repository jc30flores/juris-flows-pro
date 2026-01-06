import { describe, expect, it } from "vitest";
import { parseInvoiceDate } from "./dates";

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
});
