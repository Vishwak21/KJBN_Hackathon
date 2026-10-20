import { useState, useEffect, type FormEvent } from "react";
import { api, today, cash, message, type Row, type Page } from "./api";
import { Field, Alert, Pager } from "./shared";
type Props = { farmers: Row[]; crops: Row[]; changed: () => void };
export function DeliveryEntry({ farmers, crops, changed }: Props) {
  const [form, setForm] = useState({
    farmer_id: farmers[0]?.id ?? 0,
    crop_id: crops[0]?.id ?? 0,
    grade: crops[0]?.grades.split(",")[0] ?? "",
    gross_kg: "",
    moisture: "",
    delivered_on: today(),
  });
  const [preview, setPreview] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [checking, setChecking] = useState(false),
    [busy, setBusy] = useState(false);
  const crop = crops.find((c) => c.id === form.crop_id);
  useEffect(() => {
    setPreview(null);
    setError("");
    if (!form.gross_kg || !form.moisture || !form.farmer_id) {
      setChecking(false);
      return;
    }
    const controller = new AbortController();
    setChecking(true);
    const timer = setTimeout(() => {
      api("/api/deliveries/preview", form, "POST", controller.signal)
        .then(setPreview)
        .catch((e) => {
          if (!controller.signal.aborted) setError(message(e));
        })
        .finally(() => {
          if (!controller.signal.aborted) setChecking(false);
        });
    }, 350);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [form]);
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!preview || checking) return;
    setBusy(true);
    setError("");
    try {
      const d = await api("/api/deliveries", form);
      setNotice("Delivery #" + d.id + " saved · " + cash(d.amount));
      setForm((f) => ({ ...f, gross_kg: "", moisture: "" }));
      changed();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="entry-grid">
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>Record a delivery</h2>
            <p>Enter measured weight and moisture to check the price.</p>
          </div>
          <span className="step">01</span>
        </div>
        <form onSubmit={save}>
          <Field label="Farmer">
            <select
              value={form.farmer_id}
              onChange={(e) => setForm((f) => ({ ...f, farmer_id: Number(e.target.value) }))}
            >
              {farmers.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} · {f.village}
                </option>
              ))}
            </select>
          </Field>
          <div className="form-grid">
            <Field label="Crop">
              <select
                value={form.crop_id}
                onChange={(e) => {
                  const c = crops.find((c) => c.id === Number(e.target.value));
                  setForm((f) => ({
                    ...f,
                    crop_id: Number(e.target.value),
                    grade: c?.grades.split(",")[0] ?? "",
                  }));
                }}
              >
                {crops.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Grade">
              <select
                value={form.grade}
                onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))}
              >
                {crop?.grades.split(",").map((g: string) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
            </Field>
            <Field label="Gross weight · kg">
              <input
                required
                type="number"
                min=".001"
                step=".001"
                placeholder="e.g. 250.000"
                value={form.gross_kg}
                onChange={(e) => {
                  setNotice("");
                  setForm((f) => ({ ...f, gross_kg: e.target.value }));
                }}
              />
            </Field>
            <Field label="Moisture · %">
              <input
                required
                type="number"
                min=".01"
                step=".01"
                max={crop?.max_moisture}
                placeholder="e.g. 17.60"
                value={form.moisture}
                onChange={(e) => setForm((f) => ({ ...f, moisture: e.target.value }))}
              />
            </Field>
          </div>
          <Field label="Delivery date · IST">
            <input
              required
              type="date"
              max={today()}
              value={form.delivered_on}
              onChange={(e) => setForm((f) => ({ ...f, delivered_on: e.target.value }))}
            />
          </Field>
          {crop && (
            <p className="hint">
              Moisture threshold {crop.threshold}% · maximum accepted {crop.max_moisture}%
            </p>
          )}
          <Alert error={error} />
          {notice && (
            <p className="notice success" role="status">
              {notice}
            </p>
          )}
          <button className="primary wide" disabled={busy || checking || !preview}>
            {busy ? "Saving..." : "Save delivery"} <span>↗</span>
          </button>
        </form>
      </section>
      <div>
        <section className="panel preview">
          <div className="panel-title">
            <h2>Delivery preview</h2>
            <span className="tag">
              {checking ? "Calculating..." : preview ? "Price found" : "Live calculation"}
            </span>
          </div>
          {preview ? (
            <>
              <div className="price-number">
                {cash(preview.applied_price)}
                <small> / kg</small>
              </div>
              <p className="muted">Effective price · entry #{preview.price_id}</p>
              <dl>
                <div>
                  <dt>Gross weight</dt>
                  <dd>{preview.gross_kg} kg</dd>
                </div>
                <div>
                  <dt>Moisture deduction ({preview.deduction_pct}%)</dt>
                  <dd>− {preview.deduction_kg} kg</dd>
                </div>
                <div>
                  <dt>Net payable weight</dt>
                  <dd>{preview.net_kg} kg</dd>
                </div>
              </dl>
              <div className="total">
                <span>Delivery amount</span>
                <strong>{cash(preview.amount)}</strong>
                <small>
                  {preview.net_kg} kg · {cash(preview.applied_price)}
                </small>
              </div>
            </>
          ) : (
            <div className="empty">
              <span>↗</span>
              <p>
                {checking ? "Finding the effective price..." : "Your breakdown will appear here."}
              </p>
              <small>Choose a farmer and enter weight and moisture.</small>
            </div>
          )}
        </section>
        <div className="rule-note">
          <strong>How moisture deduction works</strong>
          <p>
            Each full percentage point above the threshold deducts 1% of gross weight, up to 10%.
            Payable money is rounded half-up to a paise.
          </p>
        </div>
      </div>
    </div>
  );
}
export function Prices({ crops, changed }: { crops: Row[]; changed: () => void }) {
  const [cropId, setCropId] = useState(crops[0]?.id ?? 0),
    [grade, setGrade] = useState(crops[0]?.grades.split(",")[0] ?? "A");
  const [list, setList] = useState<Page>({ items: [], total: 0 }),
    [page, setPage] = useState(0),
    [revision, setRevision] = useState(0);
  const [form, setForm] = useState({ price: "", effective_from: today() }),
    [newCrop, setNewCrop] = useState({
      name: "",
      grades: "A,B,C",
      threshold: "14",
      max_moisture: "28",
    });
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(false);
  const crop = crops.find((c) => c.id === cropId);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api<Page>(
      "/api/prices?crop_id=" +
        cropId +
        "&grade=" +
        encodeURIComponent(grade) +
        "&limit=25&offset=" +
        page * 25,
    )
      .then((p) => {
        if (active) setList(p);
      })
      .catch((e) => {
        if (active) setError(message(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [cropId, grade, page, revision]);
  async function add(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/prices", { crop_id: cropId, grade, ...form });
      setRevision((n) => n + 1);
      setForm((f) => ({ ...f, price: "" }));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  async function addCrop(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/crops", {
        ...newCrop,
        grades: newCrop.grades.split(",").map((g) => g.trim()),
      });
      changed();
      setNewCrop((f) => ({ ...f, name: "" }));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel">
        <div className="panel-title">
          <div>
            <h2>Effective price history</h2>
            <p>New entries append to history. Existing deliveries keep their applied price.</p>
          </div>
        </div>
        <Alert error={error} />
        <div className="form-grid">
          <Field label="Crop">
            <select
              value={cropId}
              onChange={(e) => {
                const id = Number(e.target.value);
                setCropId(id);
                setGrade(crops.find((c) => c.id === id)?.grades.split(",")[0] ?? "A");
                setPage(0);
              }}
            >
              {crops.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Grade">
            <select
              value={grade}
              onChange={(e) => {
                setGrade(e.target.value);
                setPage(0);
              }}
            >
              {crop?.grades.split(",").map((g: string) => (
                <option key={g}>{g}</option>
              ))}
            </select>
          </Field>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Entry</th>
                <th>Effective from</th>
                <th>Grade</th>
                <th>Price / kg</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((p) => (
                <tr key={p.id}>
                  <td>#{p.id}</td>
                  <td>{p.effective_from}</td>
                  <td>
                    <span className="badge">{p.grade}</span>
                  </td>
                  <td>{cash(p.price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loading ? (
          <p className="hint">Loading history...</p>
        ) : (
          !list.total && <p className="empty">No price for this combination.</p>
        )}
        <Pager page={page} total={list.total} setPage={setPage} />
        <form onSubmit={add} className="inline-form">
          <Field label="New price · ₹/kg">
            <input
              required
              type="number"
              min=".01"
              step=".01"
              value={form.price}
              onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
            />
          </Field>
          <Field label="Effective from">
            <input
              required
              type="date"
              value={form.effective_from}
              onChange={(e) => setForm((f) => ({ ...f, effective_from: e.target.value }))}
            />
          </Field>
          <button className="primary" disabled={busy || !cropId}>
            Append price
          </button>
        </form>
      </section>
      <details className="panel">
        <summary>Add a crop</summary>
        <p className="hint">
          Crop rules are immutable after creation; use a distinct name for changed quality rules.
        </p>
        <form onSubmit={addCrop}>
          <div className="form-grid">
            {(["name", "grades", "threshold", "max_moisture"] as const).map((k) => (
              <Field key={k} label={k.replaceAll("_", " ")}>
                <input
                  required
                  value={newCrop[k]}
                  onChange={(e) => setNewCrop((f) => ({ ...f, [k]: e.target.value }))}
                />
              </Field>
            ))}
          </div>
          <button className="primary" disabled={busy}>
            Create crop
          </button>
        </form>
      </details>
    </>
  );
}
