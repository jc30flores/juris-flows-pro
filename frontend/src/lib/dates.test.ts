import { describe, expect, it } from "vitest";
import { getInvoiceDateInfo } from "./dates";

describe("getInvoiceDateInfo", () => {
  it("reads issue_date and formats dd/MM/yyyy", () => {
    const info = getInvoiceDateInfo({ issue_date: "2026-01-05" });
    expect(info.dateString).toBe("2026-01-05");
    expect(info.formatted).toBe("05/01/2026");
  });

  it("falls back to date when issue_date is missing", () => {
    const info = getInvoiceDateInfo({ date: "2026-02-10" });
    expect(info.dateString).toBe("2026-02-10");
    expect(info.formatted).toBe("10/02/2026");
  });

  it("matches today based on El Salvador date without UTC rollover", () => {
    const info = getInvoiceDateInfo({ issue_date: "2026-01-05" });
    const tenPmEs = new Date("2026-01-06T04:00:00Z");
    expect(info.matchesFilter("today", tenPmEs)).toBe(true);
    expect(info.matchesFilter("today", new Date("2026-01-06T12:00:00Z"))).toBe(
      false,
    );
  });

  it("returns false when date is missing for filtered views", () => {
    const info = getInvoiceDateInfo({});
    expect(info.matchesFilter("today", new Date())).toBe(false);
  });
});
