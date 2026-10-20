import { useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { api, today, message, type Row, type Page } from "./api";
import { DeliveryEntry, Prices } from "./procurement";
import { Payouts, Ledger } from "./accounts";
import { Alert } from "./shared";
import "./style.css";
function App() {
  const [view, setView] = useState(0),
    [farmers, setFarmers] = useState<Row[]>([]),
    [crops, setCrops] = useState<Row[]>([]);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [revision, setRevision] = useState(0);
  const refresh = () => setRevision((n) => n + 1);
  useEffect(() => {
    let active = true;
    Promise.all([api<Page>("/api/farmers?limit=500"), api<Page>("/api/crops")])
      .then(([f, c]) => {
        if (active) {
          setFarmers(f.items);
          setCrops(c.items);
          setError("");
        }
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
  }, [revision]);
  const tabs = ["Delivery entry", "Price history", "Weekly payouts", "Farmer ledger"];
  return (
    <div className="app">
      <aside>
        <a className="brand" href="#">
          <b>H</b>
          <span>
            Harvest<small>Ledger</small>
          </span>
        </a>
        <p className="aside-label">BUYING CENTRE</p>
        <nav>
          {tabs.map((t, i) => (
            <button key={t} className={view === i ? "active" : ""} onClick={() => setView(i)}>
              <span>{["↗", "◷", "▤", "◎"][i]}</span>
              {t}
            </button>
          ))}
        </nav>
        <div className="aside-footer">
          ● Invented demo data<small>Problem 04 · Procurement & payout</small>
        </div>
      </aside>
      <main>
        <header>
          <span>OPERATIONS / {tabs[view].toUpperCase()}</span>
          <span>{today()} · IST</span>
        </header>
        <div className="heading">
          <div>
            <p className="eyebrow">HARVEST LEDGER</p>
            <h1>
              {
                [
                  "Every kilogram, accounted for.",
                  "A clear price for every harvest.",
                  "From delivery to a fair payout.",
                  "The complete farmer account.",
                ][view]
              }
            </h1>
            <p className="muted">Transparent weights. Effective prices. Explainable payments.</p>
          </div>
          <span className="tag">₹ INR · kg</span>
        </div>
        <Alert error={error} />
        {error && <button onClick={refresh}>Retry connection</button>}
        {loading ? (
          <section className="panel">Connecting to the buying centre...</section>
        ) : (
          <>
            {view === 0 && <DeliveryEntry farmers={farmers} crops={crops} changed={refresh} />}
            {view === 1 && <Prices crops={crops} changed={refresh} />}
            {view === 2 && <Payouts farmers={farmers} changed={refresh} />}
            {view === 3 && (
              <Ledger farmers={farmers} crops={crops} revision={revision} changed={refresh} />
            )}
          </>
        )}
        <footer>
          All payable amounts are calculated by the API. Finalised statements retain their original
          financial values.
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
