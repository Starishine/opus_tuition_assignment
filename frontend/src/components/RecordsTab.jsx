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
    Trash2,
    Search,
    Filter,
    X
} from "lucide-react";
import "../App.css";

import API from "../api";

// Records tab

const FILE_TYPE_COLS = {
    tutor_assignments: ["assignment_id", "tutor_name", "student_name", "subject", "level", "hourly_rate", "start_date", "status"],
    lesson_logs: ["lesson_id", "assignment_id", "date", "duration", "attendance", "notes", "fee"],
    invoice: ["invoice_id", "assignment_id", "student_name", "invoice_date", "payment_status", "payment_date"],
};

export default function RecordsTab() {
    const [fileType, setFileType] = useState("tutor_assignments");
    const [uploadId, setUploadId] = useState("");
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [records, setRecords] = useState([]);
    const [count, setCount] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [searched, setSearched] = useState(false);

    async function fetchRecords() {
        setLoading(true); setError(null);
        const params = new URLSearchParams({ file_type: fileType });
        if (uploadId) params.append("upload_id", uploadId);
        if (dateFrom) params.append("date_from", dateFrom);
        if (dateTo) params.append("date_to", dateTo);

        try {
            const res = await fetch(`${API}/records?${params}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail?.message || "Failed to fetch records.");
            setRecords(data.records || []);
            setCount(data.count);
            setSearched(true);
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }

    function clearFilters() {
        setUploadId(""); setDateFrom(""); setDateTo("");
        setRecords([]); setCount(null); setSearched(false);
    }

    const cols = FILE_TYPE_COLS[fileType] || [];

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 8 }}>

            {/* Filter panel */}
            <div className="card" style={{ padding: 20 }}>
                <h3 style={{ marginBottom: 16, fontSize: 15 }}>
                    <Filter size={15} style={{ marginRight: 6, verticalAlign: "middle" }} />
                    Filter Records
                </h3>

                <div className="filter-grid">
                    <div className="filter-field">
                        <label className="filter-label">File Type</label>
                        <select
                            className="filter-input"
                            value={fileType}
                            onChange={e => { setFileType(e.target.value); setRecords([]); setCount(null); setSearched(false); }}
                        >
                            <option value="tutor_assignments">Tutor Assignments</option>
                            <option value="lesson_logs">Lesson Logs</option>
                            <option value="invoice">Invoices</option>
                        </select>
                    </div>

                    <div className="filter-field">
                        <label className="filter-label">Upload ID (optional)</label>
                        <input className="filter-input" type="text" placeholder="e.g. 3f2a1b..."
                            value={uploadId} onChange={e => setUploadId(e.target.value)} />
                    </div>

                    <div className="filter-field">
                        <label className="filter-label">Date From</label>
                        <input className="filter-input" type="date"
                            value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
                    </div>

                    <div className="filter-field">
                        <label className="filter-label">Date To</label>
                        <input className="filter-input" type="date"
                            value={dateTo} onChange={e => setDateTo(e.target.value)} />
                    </div>
                </div>

                <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                    <button className="btn" onClick={fetchRecords} disabled={loading}
                        style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        {loading ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
                        {loading ? "Loading..." : "Search"}
                    </button>
                    {searched && (
                        <button className="btn-ghost" onClick={clearFilters}
                            style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <X size={14} /> Clear
                        </button>
                    )}
                </div>
            </div>

            {error && (
                <div className="alert error">
                    <AlertCircle className="icon-normal" />
                    <div className="alert-content"><strong>Error</strong><p>{error}</p></div>
                </div>
            )}

            {/* Results table */}
            {searched && !loading && (
                <div className="card" style={{ overflow: "hidden" }}>
                    <div className="card-header">
                        <span style={{ fontSize: 14 }}>
                            {count === 0 ? "No records found" : `${count} record${count !== 1 ? "s" : ""} found`}
                        </span>
                        <div className="badge">{fileType.replace("_", " ")}</div>
                    </div>

                    {records.length > 0 && (
                        <div style={{ overflowX: "auto" }}>
                            <table className="q-table" style={{ minWidth: 850 }}>
                                <thead>
                                    <tr>
                                        {cols.map(col => (
                                            <th key={col}>{col.replace(/_/g, " ")}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {records.map((row, i) => (
                                        <tr key={i}>
                                            {cols.map(col => (
                                                <td key={col}>
                                                    {row[col] == null ? <span className="muted">—</span> : String(row[col])}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}