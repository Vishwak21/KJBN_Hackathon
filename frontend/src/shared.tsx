import { cloneElement, useId, type ReactElement } from "react";
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactElement<{ "aria-labelledby"?: string }>;
}) {
  const id = useId();
  return (
    <label>
      <span id={id}>{label}</span>
      {cloneElement(children, { "aria-labelledby": id })}
    </label>
  );
}
export function Pager({
  page,
  total,
  setPage,
}: {
  page: number;
  total: number;
  setPage: (p: number) => void;
}) {
  return (
    <div className="pager">
      <button disabled={!page} onClick={() => setPage(page - 1)}>
        Previous
      </button>
      <small>
        {total} records · page {page + 1}
      </small>
      <button disabled={(page + 1) * 25 >= total} onClick={() => setPage(page + 1)}>
        Next
      </button>
    </div>
  );
}
export function Alert({ error }: { error: string }) {
  return error ? (
    <div className="error notice" role="alert">
      {error}
    </div>
  ) : null;
}
