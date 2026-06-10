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

import QuarantineTable from "./QuarantineTable";
import "../App.css";

const API = "http://localhost:8000";

function MetricCard({ label, value, className = "" }) {
    return (
        <div className="metric">
            <div className="label">{label}</div>
            <div className={`value ${className}`}>{value}</div>
        </div>
    );
}

export default function UploadTab({ onUploadComplete }) {
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
            console.log(data);

            if (!res.ok) {
                let errorObj = { title: "Upload Failed", message: "An unexpected error occurred on the server." };

                if (data?.detail?.error && data?.detail?.message) {
                    // Replaces underscores with spaces for a cleaner title (e.g., "UNSUPPORTED FILE TYPE")
                    errorObj.title = data.detail.error.replace(/_/g, " ");
                    errorObj.message = data.detail.message;
                } else if (typeof data?.detail === "string") {
                    errorObj.message = data.detail;
                } else if (!isJson) {
                    errorObj.message = `Server Error ${res.status}: ${res.statusText}. Is the backend running?`;
                }

                setError(errorObj);
                return; // Exit early, the finally block will still run to clear loading state
            }

            setResult(data);
            onUploadComplete?.();

        } catch (err) {
            setError({
                title: "Network Error",
                message: err.message || "Failed to connect to the server."
            });
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
                        <strong style={{ textTransform: "capitalize" }}>
                            {error.title || "Upload Failed"}
                        </strong>
                        <p>{error.message || error}</p>
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