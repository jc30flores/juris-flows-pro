type DteIdent = {
  numeroControl?: string;
  codigoGeneracion?: string;
  codigo_generacion?: string;
  numero_control?: string;
};

const pickFirst = <T>(...values: Array<T | null | undefined>): T | null => {
  for (const value of values) {
    if (value !== null && value !== undefined && String(value).trim() !== "") {
      return value as T;
    }
  }
  return null;
};

export const getDteIdent = (invoice: unknown): DteIdent | null => {
  const source = invoice as Record<string, unknown> | null;
  if (!source) return null;

  const dteContainer = pickFirst<Record<string, unknown>>(
    source.dte as Record<string, unknown> | undefined,
    source.dte_data as Record<string, unknown> | undefined,
    source.dteJson as Record<string, unknown> | undefined,
    source.dte_json as Record<string, unknown> | undefined,
    source.dte_payload as Record<string, unknown> | undefined,
    (source.hacienda_request as Record<string, unknown> | undefined)?.dte as
      | Record<string, unknown>
      | undefined,
    (source.hacienda_response as Record<string, unknown> | undefined)?.dte as
      | Record<string, unknown>
      | undefined,
    source.dte_document as Record<string, unknown> | undefined,
    source.dte_documento as Record<string, unknown> | undefined,
  );

  const dteRecord = dteContainer ?? source;

  const recordObject = dteRecord as Record<string, unknown>;
  const ident = pickFirst<Record<string, unknown>>(
    recordObject.identificacion as Record<string, unknown> | undefined,
    (recordObject.dte as Record<string, unknown> | undefined)?.identificacion as
      | Record<string, unknown>
      | undefined,
    (recordObject.documento as Record<string, unknown> | undefined)?.identificacion as
      | Record<string, unknown>
      | undefined,
    (recordObject.data as Record<string, unknown> | undefined)?.identificacion as
      | Record<string, unknown>
      | undefined,
    source.identificacion as Record<string, unknown> | undefined,
  );

  const identData = ident ?? {};

  const numeroControl = pickFirst(
    (identData as Record<string, unknown>).numeroControl as string | undefined,
    (identData as Record<string, unknown>).numero_control as string | undefined,
    recordObject.numeroControl as string | undefined,
    recordObject.numero_control as string | undefined,
    source.numeroControl as string | undefined,
    source.numero_control as string | undefined,
  );

  const codigoGeneracion = pickFirst(
    (identData as Record<string, unknown>).codigoGeneracion as string | undefined,
    (identData as Record<string, unknown>).codigo_generacion as string | undefined,
    recordObject.codigoGeneracion as string | undefined,
    recordObject.codigo_generacion as string | undefined,
    source.codigoGeneracion as string | undefined,
    source.codigo_generacion as string | undefined,
  );

  if (!numeroControl && !codigoGeneracion) return null;

  return {
    numeroControl: numeroControl ? String(numeroControl) : undefined,
    codigoGeneracion: codigoGeneracion ? String(codigoGeneracion) : undefined,
  };
};

export const getNumeroControl = (invoice: unknown): string | null => {
  const ident = getDteIdent(invoice);
  return ident?.numeroControl ? String(ident.numeroControl) : null;
};

export const getCodigoGeneracion = (invoice: unknown): string | null => {
  const ident = getDteIdent(invoice);
  return ident?.codigoGeneracion ? String(ident.codigoGeneracion) : null;
};

export const upperOrDash = (value: string | null): string => {
  return value ? value.toUpperCase() : "—";
};
