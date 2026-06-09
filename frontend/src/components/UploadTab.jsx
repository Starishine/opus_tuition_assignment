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