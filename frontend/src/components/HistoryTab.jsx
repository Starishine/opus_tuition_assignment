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
import "../App.css";

const API = "http://localhost:8000";

// Helper functions and components
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

export default function HistoryTab() {
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