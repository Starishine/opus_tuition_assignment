import { useState, useRef, useCallback, useEffect } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle,
  Loader2,
  History,
  ChevronUp,
  ChevronDown,
  Trash2
} from "lucide-react";
import "./App.css";

const API = "http://localhost:8000";

// helper functions

function MetricCard({ label, value, className = "" }) {
  return (
    <div className="metric">
      <div className="label">{label}</div>
      <div className={`value ${className}`}>{value}</div>
    </div>
  );
}

function QuarantineTable({ rows }) {
  if (!rows?.length) return null;
  return (
    <div className="quarantine">
      <h4 className="quarantine-title">
        <FileSpreadsheet className="icon-small" /> Quarantine Log
      </h4>
      <div className="quarantine-box">
        <table className="q-table">
          <thead>
            <tr>
              <th>Row</th>
              <th>Code</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((q, i) => (
              <tr key={i}>
                <td>{q.row_number ?? "—"}</td>
                <td><span className="badge danger">{q.reason_code}</span></td>
                <td>{q.reason_detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Upload Tab Component

function UploadTab({ onUploadComplete }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const uploadFile = useCallback(async (file) => {
    if (!file) return;
    setError(null);
    setResult(null);
    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });

      // Safely check for JSON
      const isJson = res.headers.get("content-type")?.includes("application/json");
      const data = isJson ? await res.json() : null;

      if (!res.ok) {
        let errorMessage = "An unexpected error occurred on the server.";

        if (data?.detail?.message) {
          errorMessage = data.detail.message;
        } else if (typeof data?.detail === "string") {
          errorMessage = data.detail;
        } else if (!isJson) {
          errorMessage = `Server Error ${res.status}: ${res.statusText}. Is the backend running?`;
        }

        throw new Error(errorMessage);
      }

      setResult(data);
      onUploadComplete?.();

    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
      setIsDragging(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, [onUploadComplete]);

  return (
    <>
      <section
        className={`dropzone ${loading ? "loading" : ""} ${isDragging ? "dragging" : ""}`}
        onClick={() => !loading && fileInputRef.current?.click()}
        onDrop={e => { e.preventDefault(); setIsDragging(false); uploadFile(e.dataTransfer?.files?.[0]); }}
        onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setIsDragging(true); }}
        onDragLeave={e => { e.preventDefault(); setIsDragging(false); }}
      >
        <input
          type="file"
          accept=".xlsx,.csv"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={e => uploadFile(e.target.files?.[0])}
        />
        <div className="drop-inner">
          {loading ? (
            <div className="loading-state">
              <Loader2 className="spin icon-large" />
              <p>Processing pipeline...</p>
            </div>
          ) : (
            <>
              <UploadCloud className="icon-large accent-color" />
              <h3>Click to upload or drag and drop</h3>
              <p className="muted">Excel (.xlsx) or CSV (.csv) only</p>
              <button type="button" className="btn">Browse Files</button>
            </>
          )}
        </div>
      </section>

      {error && (
        <div className="alert error">
          <AlertCircle className="icon-normal" />
          <div className="alert-content">
            <strong>Upload Failed</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {result && (
        <div className="card result-card">
          <div className="card-header">
            <div className="title">
              <CheckCircle className="success-color icon-normal" />
              <h2>Pipeline Complete</h2>
            </div>
            <div className="badge">{result.file_type}</div>
          </div>
          <div className="metrics">
            <MetricCard label="Rows Received" value={result.rows_received} />
            <MetricCard label="Accepted" value={result.rows_accepted} className="success-color" />
            <MetricCard label="Quarantined" value={result.rows_quarantined}
              className={result.rows_quarantined > 0 ? "danger-color" : ""} />
          </div>
          <QuarantineTable rows={result.quarantine} />
          <div className="card-footer muted">Upload ID: {result.upload_id}</div>
        </div>
      )}
    </>
  );
}

// History Tab Component

function HistoryTab() {
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [report, setReport] = useState(null);
  const [reportLoading, setRepLoading] = useState(false);

  useEffect(() => { fetchUploads(); }, []);

  // Fetch list of uploads with summary info
  async function fetchUploads() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/all_uploads`);
      const data = await res.json();
      setUploads(data.uploads || []);
    } finally {
      setLoading(false);
    }
  }

  // Fetch detailed report for a specific upload
  async function toggleReport(upload_id) {
    if (expanded === upload_id) {
      setExpanded(null);
      setReport(null);
      return;
    }
    setExpanded(upload_id);
    setRepLoading(true);
    try {
      const res = await fetch(`${API}/report/${upload_id}`);
      const data = await res.json();
      console.log("Fetched report for upload_id %s: %o", upload_id, data);
      setReport(data);
    } finally {
      setRepLoading(false);
    }
  }

  async function handleDelete(upload_id) {
    if (!window.confirm(`Delete upload ${upload_id}? This cannot be undone.`))
      return;

    await fetch(`${API}/uploads/${upload_id}`, { method: "DELETE" });
    fetchUploads();
    if (expanded === upload_id) {
      setExpanded(null); setReport(null);
    }
  }

  if (loading) return <div className="loading-state"><Loader2 className="spin icon-large" /></div>;
  if (!uploads.length) return <p className="muted" style={{ textAlign: "center", marginTop: "2rem" }}>No uploads yet.</p>;

  return (
    <div className="history-list">
      {uploads.map(u => (
        <div key={u.upload_id} className="history-row card">
          <div className="history-summary">
            <div>
              <strong>{u.file_name}</strong>
              <span className="badge" style={{ marginLeft: 8 }}>{u.file_type}</span>
            </div>
            <div className="history-meta muted">
              {new Date(u.uploaded_at).toLocaleString()} ·
              <span className="success-color"> {u.rows_accepted} accepted</span> ·
              <span className={u.rows_quarantined > 0 ? " danger-color" : ""}> {u.rows_quarantined} quarantined</span>
            </div>
          </div>

          <div className="history-actions">
            <button className="btn-ghost" onClick={() => toggleReport(u.upload_id)}>
              {expanded === u.upload_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              Report
            </button>
            <button className="btn-ghost danger" onClick={() => handleDelete(u.upload_id)}>
              <Trash2 size={16} /> Delete
            </button>
          </div>

          {expanded === u.upload_id && (
            <div className="report-panel">
              {reportLoading ? (
                <Loader2 className="spin" />
              ) : report ? (
                <>
                  <div className="metrics" style={{ marginBottom: 16 }}>
                    <MetricCard label="Received" value={report.rows_received} />
                    <MetricCard label="Accepted" value={report.rows_accepted} className="success-color" />
                    <MetricCard label="Quarantined" value={report.rows_quarantined}
                      className={report.rows_quarantined > 0 ? "danger-color" : ""} />
                  </div>

                  {report.quarantine_breakdown?.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <h4>Quarantine Breakdown</h4>
                      <table className="q-table">
                        <thead><tr><th>Reason</th><th>Count</th></tr></thead>
                        <tbody>
                          {report.quarantine_breakdown.map((b, i) => (
                            <tr key={i}>
                              <td><span className="badge danger">{b.reason_code}</span></td>
                              <td>{b.count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <QuarantineTable rows={report.quarantine_rows} />
                </>
              ) : null}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// Root App Component

export default function App() {
  const [tab, setTab] = useState("upload");
  const [historyKey, setHistoryKey] = useState(0);

  return (
    <div className="app-root">
      <div className="container">
        <header className="app-header">
          <div>
            <h1>OPUS Data Ingestion</h1>
            <p className="muted">Upload tutor assignments, lesson logs, or invoices for validation.</p>
          </div>
          <nav className="tabs">
            <button className={`tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>
              <UploadCloud size={16} /> Upload
            </button>
            <button className={`tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
              <History size={16} /> History
            </button>
          </nav>
        </header>

        <main>
          {tab === "upload" && <UploadTab onUploadComplete={() => setHistoryKey(k => k + 1)} />}
          {tab === "history" && <HistoryTab key={historyKey} />}
        </main>
      </div>
    </div>
  );
}