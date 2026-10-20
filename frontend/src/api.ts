export type Row = { id: number; [key: string]: any };
export type Page = { items: Row[]; total: number };
const env = (import.meta as ImportMeta & { env: { VITE_API_BASE_URL?: string } }).env;
const base = (env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export async function api<T = Row>(
  path: string,
  data?: unknown,
  method = "POST",
  signal?: AbortSignal,
): Promise<T> {
  const r = await fetch(base + path, {
    method: data === undefined ? "GET" : method,
    headers: data === undefined ? undefined : { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
    signal,
  });
  const result = await r.json();
  if (!r.ok)
    throw Error(
      (result.error?.message ?? "Request failed") +
        (result.error?.details
          ?.map((d: { field: string; message: string }) => " " + d.field + ": " + d.message)
          .join("") ?? "") +
        " [ref " +
        (result.error?.request_id ?? "unknown").slice(0, 8) +
        "]",
    );
  return result;
}
// Format decimal strings directly: converting money to Number loses paise at large values.
export const cash = (value: string | number) => {
  const [whole, fraction = ""] = String(value).split(".");
  const negative = whole.startsWith("-");
  const digits = whole.replace("-", "");
  const tail = digits.slice(-3),
    lead = digits.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  return (
    (negative ? "-" : "") +
    "\u20b9" +
    (lead ? lead + "," : "") +
    tail +
    "." +
    fraction.padEnd(2, "0").slice(0, 2)
  );
};
export const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const stamp = (value: string) =>
  new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value)) + " IST";
export const message = (e: unknown) =>
  e instanceof Error ? e.message : "Unable to complete request.";
