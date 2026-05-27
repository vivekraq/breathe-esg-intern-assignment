import React, { useEffect, useMemo, useState } from "react";
import { Check, FileUp, Filter, Lock, RefreshCcw, Search, X } from "lucide-react";
import { createRoot } from "react-dom/client";
import "./style.css";

const API = import.meta.env.VITE_API_BASE_URL || "/api";
const ORG = "acme-industrials";

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "X-Org-Slug": ORG,
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function fmt(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (!Number.isNaN(Number(value))) return Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
  return value;
}

function App() {
  const [dashboard, setDashboard] = useState(null);
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    setBusy(true);
    try {
      const [dash, rows, batchRows] = await Promise.all([
        api("/dashboard/"),
        api(`/records/?${new URLSearchParams({ status, source }).toString()}`),
        api("/batches/"),
      ]);
      setDashboard(dash);
      setRecords(rows);
      setBatches(batchRows);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load().catch((error) => setMessage(error.message));
  }, [status, source]);

  async function upload(kind, file) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const result = await api(`/ingest/${kind}/`, { method: "POST", body });
      setMessage(`Imported ${result.rows} ${kind} rows; ${result.failed} need attention.`);
      await load();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function review(record, action) {
    setBusy(true);
    try {
      const updated = await api(`/records/${record.id}/review/`, {
        method: "POST",
        body: JSON.stringify({ action, actor: "analyst@breatheesg.com" }),
      });
      setRecords((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelected(updated);
      await loadAudit(updated);
      await load();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadAudit(record) {
    setSelected(record);
    setAudit(await api(`/records/${record.id}/audit/`));
  }

  const filteredRecords = useMemo(() => {
    const term = query.toLowerCase();
    return records.filter((row) =>
      [row.external_id, row.source_name, row.activity_type, row.category, row.facility?.name]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(term))
    );
  }, [records, query]);

  const counts = dashboard?.counts || {};

  return (
    <main className="app">
      <header className="topbar">
        <div>
          <p className="eyebrow">Breathe ESG</p>
          <h1>Analyst ingestion review</h1>
        </div>
        <button className="iconButton" onClick={load} disabled={busy} title="Refresh">
          <RefreshCcw size={18} />
        </button>
      </header>

      <section className="metrics">
        {[
          ["Total rows", counts.total],
          ["Need review", (counts.pending || 0) + (counts.needs_fix || 0)],
          ["Suspicious", counts.suspicious],
          ["Approved", counts.approved],
          ["Locked", counts.locked],
        ].map(([label, value]) => (
          <div className="metric" key={label}>
            <span>{label}</span>
            <strong>{value || 0}</strong>
          </div>
        ))}
      </section>

      <section className="workbench">
        <aside className="sidebar">
          <h2>Imports</h2>
          <UploadButton label="SAP OData CSV" kind="sap" onUpload={upload} />
          <UploadButton label="Utility CSV" kind="utility" onUpload={upload} />
          <UploadButton label="Concur export" kind="travel" onUpload={upload} />
          <div className="batchList">
            <h3>Latest batches</h3>
            {batches.slice(0, 6).map((batch) => (
              <div className="batch" key={batch.id}>
                <strong>{batch.source_system.name}</strong>
                <span>{batch.row_count} rows, {batch.failed_count} flagged</span>
              </div>
            ))}
          </div>
        </aside>

        <section className="review">
          <div className="toolbar">
            <div className="search">
              <Search size={16} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search rows" />
            </div>
            <label className="select">
              <Filter size={16} />
              <select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">Pending</option>
                <option value="needs_fix">Needs fix</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="locked">Locked</option>
              </select>
            </label>
            <select className="plainSelect" value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="">All sources</option>
              <option value="sap_odata">SAP</option>
              <option value="utility_csv">Utility</option>
              <option value="concur_export">Travel</option>
            </select>
          </div>

          {message && <div className="notice">{message}</div>}

          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Activity</th>
                  <th>Period</th>
                  <th>Scope</th>
                  <th>Quantity</th>
                  <th>CO2e kg</th>
                  <th>Status</th>
                  <th>Flags</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map((record) => (
                  <tr key={record.id} onClick={() => loadAudit(record)}>
                    <td>
                      <strong>{record.external_id}</strong>
                      <span>{record.source_name}</span>
                    </td>
                    <td>
                      <strong>{record.activity_type}</strong>
                      <span>{record.facility?.name || record.category.replaceAll("_", " ")}</span>
                    </td>
                    <td>{record.period_start || record.activity_date} to {record.period_end || record.activity_date}</td>
                    <td>{record.scope.replace("_", " ")}</td>
                    <td>{fmt(record.normalized_quantity)} {record.normalized_unit}</td>
                    <td>{fmt(record.co2e_kg)}</td>
                    <td><span className={`pill ${record.review_status}`}>{record.review_status.replace("_", " ")}</span></td>
                    <td className="flags">{record.suspicious_flags.length ? record.suspicious_flags.join(", ") : "-"}</td>
                    <td>
                      <div className="rowActions">
                        <button title="Approve" onClick={(event) => { event.stopPropagation(); review(record, "approve"); }}><Check size={16} /></button>
                        <button title="Reject" onClick={(event) => { event.stopPropagation(); review(record, "reject"); }}><X size={16} /></button>
                        <button title="Lock" onClick={(event) => { event.stopPropagation(); review(record, "lock"); }}><Lock size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="detail">
          <h2>Audit trail</h2>
          {selected ? (
            <>
              <div className="detailHead">
                <strong>{selected.external_id}</strong>
                <span>{selected.emission_factor_ref}</span>
              </div>
              <pre>{JSON.stringify(selected.source_payload, null, 2)}</pre>
              <h3>Events</h3>
              {audit.length ? audit.map((event) => (
                <div className="event" key={event.id}>
                  <strong>{event.action}</strong>
                  <span>{event.actor} at {new Date(event.created_at).toLocaleString()}</span>
                </div>
              )) : <p className="muted">No review actions yet.</p>}
            </>
          ) : (
            <p className="muted">Select a row to inspect source payload and approval history.</p>
          )}
        </aside>
      </section>
    </main>
  );
}

function UploadButton({ label, kind, onUpload }) {
  return (
    <label className="upload">
      <FileUp size={18} />
      <span>{label}</span>
      <input type="file" accept=".csv,text/csv" onChange={(event) => onUpload(kind, event.target.files?.[0])} />
    </label>
  );
}

createRoot(document.getElementById("root")).render(<App />);
