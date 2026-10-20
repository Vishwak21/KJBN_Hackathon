import { useState, useEffect, type FormEvent } from "react";
import { api, today, cash, stamp, message, type Row, type Page } from "./api";
import { Field, Alert, Pager } from "./shared";
export function Payouts({ farmers, changed }: { farmers: Row[]; changed: () => void }) {
  const [farmer, setFarmer] = useState(farmers[0]?.id ?? 0),
    [week, setWeek] = useState(today()),
    [list, setList] = useState<Page>({ items: [], total: 0 }),
    [selected, setSelected] = useState<Row | null>(null);
  const [page, setPage] = useState(0),
    [revision, setRevision] = useState(0),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [confirm, setConfirm] = useState(false);
  useEffect(() => {
    let active = true;
    api<Page>("/api/payouts?farmer_id=" + farmer + "&limit=25&offset=" + page * 25)
      .then((p) => {
        if (active) setList(p);
      })
      .catch((e) => {
        if (active) setError(message(e));
      });
    return () => {
      active = false;
    };
  }, [farmer, page, revision]);
  async function perform(path: string, data?: unknown) {
    setBusy(true);
    setError("");
    setConfirm(false);
    try {
      setSelected(await api(path, data));
      setRevision((n) => n + 1);
      changed();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel">
        <h2>Weekly statements</h2>
        <form
          className="inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            void perform("/api/payouts", { farmer_id: farmer, week });
          }}
        >
          <Field label="Farmer">
            <select
              value={farmer}
              onChange={(e) => {
                setFarmer(Number(e.target.value));
                setSelected(null);
                setPage(0);
              }}
            >
              {farmers.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Any date in the week">
            <input required type="date" value={week} onChange={(e) => setWeek(e.target.value)} />
          </Field>
          <button className="primary" disabled={busy || !farmer}>
            Generate / refresh draft
          </button>
        </form>
        <p className="hint">
          Monday?Sunday · drafts reserve deliveries. Recovery is recalculated at finalisation.
        </p>
        <Alert error={error} />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Statement</th>
                <th>Week starting</th>
                <th>Status</th>
                <th>Gross</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.items.map((p) => (
                <tr key={p.id}>
                  <td>#{p.id}</td>
                  <td>{p.week}</td>
                  <td>
                    <span className={"badge " + p.status.toLowerCase()}>{p.status}</span>
                  </td>
                  <td>{cash(p.gross)}</td>
                  <td>
                    <button
                      disabled={busy}
                      className="text-button"
                      onClick={() => perform("/api/payouts/" + p.id)}
                    >
                      View →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!list.total && (
          <p className="empty">No statements yet. Record deliveries and generate a draft.</p>
        )}
        <Pager page={page} total={list.total} setPage={setPage} />
      </section>
      {selected && (
        <section className="panel">
          <div className="panel-title">
            <div>
              <p className="eyebrow">PAYOUT #{selected.id}</p>
              <h2>{farmers.find((f) => f.id === selected.farmer_id)?.name}</h2>
              <p>Week starting {selected.week} · Monday?Sunday</p>
            </div>
            <span className={"badge " + selected.status.toLowerCase()}>{selected.status}</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Delivery / date</th>
                  <th>Gross kg</th>
                  <th>Deduction kg</th>
                  <th>Net kg · price</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {selected.deliveries.map((d: Row) => (
                  <tr key={d.id}>
                    <td>
                      #{d.id}
                      <small className="block">{d.delivered_on}</small>
                      {d.original_id && (
                        <small className="block">
                          For #{d.original_id}: {d.reason}
                        </small>
                      )}
                    </td>
                    <td>{d.gross_kg ?? "?"}</td>
                    <td>{d.deduction_kg ?? "?"}</td>
                    <td>
                      {d.original_id ? "Adjustment" : d.net_kg + " · " + cash(d.applied_price)}
                    </td>
                    <td>{cash(d.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="totals-row">
            {[
              ["Sum of delivery amounts", selected.gross],
              ["Advance recovery · up to 30%", selected.deduction],
              ["Net payout", selected.net],
            ].map(([label, value]) => (
              <div className="money" key={label}>
                <span>{label}</span>
                <strong>{cash(value)}</strong>
              </div>
            ))}
          </div>
          <p className="hint">
            Net = gross · advance recovery. Created {stamp(selected.created_at)}.
            {selected.finalised_at && " Finalised " + stamp(selected.finalised_at) + "."}
          </p>
          {selected.status === "Draft" &&
            (confirm ? (
              <div className="notice">
                <p>
                  Finalising freezes the statement and reduces the outstanding advance. Current
                  outstanding will be checked again.
                </p>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => perform("/api/payouts/" + selected.id + "/finalise", {})}
                >
                  Confirm finalisation
                </button>{" "}
                <button onClick={() => setConfirm(false)}>Cancel</button>
              </div>
            ) : (
              <button className="primary" disabled={busy} onClick={() => setConfirm(true)}>
                Finalise statement
              </button>
            ))}
          {selected.status === "Finalised" && (
            <button
              className="primary"
              disabled={busy}
              onClick={() => perform("/api/payouts/" + selected.id + "/pay", {})}
            >
              Mark as paid
            </button>
          )}
        </section>
      )}
    </>
  );
}
export function Ledger({
  farmers,
  crops,
  revision,
  changed,
}: {
  farmers: Row[];
  crops: Row[];
  revision: number;
  changed: () => void;
}) {
  const [farmer, setFarmer] = useState(farmers[0]?.id ?? 0),
    [data, setData] = useState<Row | null>(null),
    [page, setPage] = useState(0),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [person, setPerson] = useState({ name: "", phone: "", village: "", bank_reference: "" }),
    [advance, setAdvance] = useState({ amount: "", given_on: today() });
  const [note, setNote] = useState({ original: "", amount: "", delivered_on: today(), reason: "" }),
    [editing, setEditing] = useState<Row | null>(null);
  useEffect(() => {
    let active = true;
    if (!farmer) return;
    api("/api/farmers/" + farmer + "/ledger?limit=25&offset=" + page * 25)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(message(e));
      });
    return () => {
      active = false;
    };
  }, [farmer, page, revision]);
  async function perform(path: string, values: unknown, text: string, method = "POST") {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(path, values, method);
      setNotice(text);
      changed();
      return true;
    } catch (e) {
      setError(message(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function edit(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const d = editing;
    const ok = await perform(
      "/api/deliveries/" + d.id,
      {
        farmer_id: d.farmer_id,
        crop_id: d.crop_id,
        grade: d.grade,
        gross_kg: d.gross_kg,
        moisture: d.moisture,
        delivered_on: d.delivered_on,
      },
      "Delivery updated.",
      "PUT",
    );
    if (ok) setEditing(null);
  }
  return (
    <>
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>Farmer account</h2>
            <p>Deliveries, advances and payout history in one place.</p>
          </div>
          <Field label="Select farmer">
            <select
              value={farmer}
              onChange={(e) => {
                setFarmer(Number(e.target.value));
                setData(null);
                setEditing(null);
                setPage(0);
                setError("");
                setNotice("");
              }}
            >
              {farmers.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Alert error={error} />
        {notice && (
          <div className="notice success" role="status">
            {notice}
          </div>
        )}
        {data ? (
          <>
            <div className="account-banner">
              <div>
                <h2>{data.farmer.name}</h2>
                <p>
                  {data.farmer.village} · {data.farmer.phone}
                </p>
                <small>Bank reference: {data.farmer.bank_reference || "Not supplied"}</small>
              </div>
              <div className="money">
                <span>Outstanding advance</span>
                <strong>{cash(data.outstanding)}</strong>
              </div>
            </div>
            <h3>Deliveries & adjustments</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>ID / date</th>
                    <th>Produce</th>
                    <th>Weight / note</th>
                    <th>Amount</th>
                    <th>Statement</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {data.deliveries.map((d: Row) => (
                    <tr key={d.id}>
                      <td>
                        #{d.id}
                        <small className="block">{d.delivered_on}</small>
                      </td>
                      <td>
                        {crops.find((c) => c.id === d.crop_id)?.name} / {d.grade}
                      </td>
                      <td>
                        {d.original_id
                          ? "For #" + d.original_id + ": " + d.reason
                          : d.net_kg + " kg net"}
                      </td>
                      <td>{cash(d.amount)}</td>
                      <td>{d.payout_id ? "#" + d.payout_id : "Unassigned"}</td>
                      <td>
                        {!d.payout_id && !d.original_id ? (
                          <button className="text-button" onClick={() => setEditing(d)}>
                            Edit
                          </button>
                        ) : !d.original_id ? (
                          <button
                            className="text-button"
                            onClick={() => setNote((n) => ({ ...n, original: String(d.id) }))}
                          >
                            Correction →
                          </button>
                        ) : (
                          "Locked"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data.deliveries_total && <p className="empty">No deliveries yet.</p>}
            <div className="form-grid">
              <div>
                <h3>Advances ({data.advances_total})</h3>
                {data.advances.map((a: Row) => (
                  <div className="ledger-row" key={a.id}>
                    <span>
                      #{a.id} · {a.given_on}
                    </span>
                    <strong>{cash(a.amount)}</strong>
                  </div>
                ))}
              </div>
              <div>
                <h3>Payouts ({data.payouts_total})</h3>
                {data.payouts.map((p: Row) => (
                  <div className="ledger-row" key={p.id}>
                    <span>
                      #{p.id} · {p.week} · {p.status}
                    </span>
                    <strong>{cash(p.net)}</strong>
                  </div>
                ))}
              </div>
            </div>
            <Pager
              page={page}
              total={Math.max(data.deliveries_total, data.advances_total, data.payouts_total)}
              setPage={setPage}
            />
          </>
        ) : (
          <p className="empty">{farmer ? "Loading account..." : "Add a farmer to get started."}</p>
        )}
      </section>
      {editing && (
        <section className="panel">
          <h2>Edit unassigned delivery #{editing.id}</h2>
          <form onSubmit={edit}>
            <div className="form-grid">
              {(["gross_kg", "moisture", "delivered_on"] as const).map((k) => (
                <Field key={k} label={k.replaceAll("_", " ")}>
                  <input
                    required
                    type={k === "delivered_on" ? "date" : "number"}
                    step={k === "gross_kg" ? ".001" : ".01"}
                    min={k === "delivered_on" ? undefined : ".001"}
                    value={editing[k]}
                    onChange={(e) => setEditing((d) => d && { ...d, [k]: e.target.value })}
                  />
                </Field>
              ))}
            </div>
            <button className="primary" disabled={busy}>
              Save changes
            </button>{" "}
            <button type="button" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </form>
        </section>
      )}
      <div className="form-grid">
        <details className="panel">
          <summary>Record an advance</summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void perform("/api/advances", { farmer_id: farmer, ...advance }, "Advance recorded.");
            }}
          >
            <Field label="Amount · ₹">
              <input
                required
                type="number"
                step=".01"
                min=".01"
                value={advance.amount}
                onChange={(e) => setAdvance((a) => ({ ...a, amount: e.target.value }))}
              />
            </Field>
            <Field label="Given on">
              <input
                required
                type="date"
                max={today()}
                value={advance.given_on}
                onChange={(e) => setAdvance((a) => ({ ...a, given_on: e.target.value }))}
              />
            </Field>
            <button className="primary" disabled={busy || !farmer}>
              Record advance
            </button>
          </form>
        </details>
        <details open={!!note.original} className="panel">
          <summary>Credit / debit correction</summary>
          <p className="hint">
            Reference a regular delivery in a finalised or paid statement. Date the correction in a
            later week. Negative amounts reduce the payout.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const { original, ...values } = note;
              void perform(
                "/api/deliveries/" + Number(original) + "/corrections",
                values,
                "Correction recorded.",
              );
            }}
          >
            {(["original", "amount", "delivered_on", "reason"] as const).map((k) => (
              <Field
                key={k}
                label={
                  {
                    original: "Original delivery ID",
                    amount: "Signed adjustment · ₹",
                    delivered_on: "Correction date",
                    reason: "Reason",
                  }[k]
                }
              >
                <input
                  required
                  type={k === "delivered_on" ? "date" : k === "reason" ? "text" : "number"}
                  step=".01"
                  maxLength={120}
                  value={note[k]}
                  onChange={(e) => setNote((n) => ({ ...n, [k]: e.target.value }))}
                />
              </Field>
            ))}
            <button className="primary" disabled={busy}>
              Record correction
            </button>
          </form>
        </details>
      </div>
      <details className="panel">
        <summary>Add a farmer</summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void perform(
              "/api/farmers",
              person,
              "Farmer created. Select them in the account list.",
            );
          }}
        >
          <div className="form-grid">
            {(["name", "phone", "village", "bank_reference"] as const).map((k) => (
              <Field key={k} label={k.replaceAll("_", " ")}>
                <input
                  required={k !== "bank_reference"}
                  maxLength={120}
                  value={person[k]}
                  onChange={(e) => setPerson((p) => ({ ...p, [k]: e.target.value }))}
                />
              </Field>
            ))}
          </div>
          <button className="primary" disabled={busy}>
            Create farmer
          </button>
        </form>
      </details>
    </>
  );
}
