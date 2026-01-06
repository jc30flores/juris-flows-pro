export function renderCellValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  const valueType = typeof value;
  if (valueType === "string" || valueType === "number" || valueType === "boolean") {
    return String(value);
  }
  if (valueType === "object") {
    const record = value as Record<string, unknown>;
    const candidate =
      record["name"] ??
      record["code"] ??
      record["label"] ??
      record["title"] ??
      record["full_name"] ??
      record["id"];
    if (candidate !== undefined && candidate !== null) return String(candidate);
    return "[obj]";
  }
  return String(value);
}
