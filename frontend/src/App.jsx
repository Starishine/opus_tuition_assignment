import { useState, useRef, useCallback } from "react";
import { UploadCloud, FileSpreadsheet, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import "./App.css"; // Ensure this matches your CSS file name

export default function App() {
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
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail?.message || "Failed to process file.");
      }

      setResult(data);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, []);

  function handleInputChange(e) {
    const file = e.target.files?.[0];
    uploadFile(file);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    uploadFile(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
    setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  return (
    <div className="app-root">
      <div className="container">
        <header className="app-header">
          <div>
            <h1>OPUS Data Ingestion</h1>
            <p className="muted">Upload tutor assignments, lesson logs, or invoices for validation.</p>
          </div>
        </header>

        <main>
          <section
            className={`dropzone ${loading ? "loading" : ""} ${isDragging ? "dragging" : ""}`}
            onClick={() => !loading && fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            {/* The native input is now strictly hidden */}
            <input
              type="file"
              accept=".xlsx,.csv"
              onChange={handleInputChange}
              ref={fileInputRef}
              style={{ display: 'none' }}
            />

            <div className="drop-inner">
              {loading ? (
                <div className="loading-state">
                  <Loader2 className="spin icon-large" />
                  <p>Processing your data pipeline...</p>
                </div>
              ) : (
                <>
                  <UploadCloud className="icon-large accent-color" />
                  <h3>Click to upload or drag and drop</h3>
                  <p className="muted">Excel (.xlsx) or CSV files only • Max 10MB</p>
                  <button type="button" className="btn">
                    Browse Files
                  </button>
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
                <div className="metric">
                  <div className="label">Rows Received</div>
                  <div className="value">{result.rows_received}</div>
                </div>
                <div className="metric">
                  <div className="label">Accepted</div>
                  <div className="value success-color">{result.rows_accepted}</div>
                </div>
                <div className="metric">
                  <div className="label">Quarantined</div>
                  <div className={`value ${result.rows_quarantined > 0 ? "danger-color" : ""}`}>
                    {result.rows_quarantined}
                  </div>
                </div>
              </div>

              {result.rows_quarantined > 0 && (
                <div className="quarantine">
                  <h4 className="quarantine-title">
                    <FileSpreadsheet className="icon-small" /> Quarantine Log
                  </h4>
                  <div className="quarantine-box">
                    <pre>{JSON.stringify(result.quarantine, null, 2)}</pre>
                  </div>
                </div>
              )}

              <div className="card-footer">Upload ID: {result.upload_id}</div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}