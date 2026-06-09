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
import "./App.css";

import UploadTab from "./components/UploadTab";
import HistoryTab from "./components/HistoryTab";
import RecordsTab from "./components/RecordsTab";


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
          <nav className="tabs" style={{ marginTop: 20 }}>
            <button className={`tab ${tab === "upload" ? "active" : ""}`} onClick={() => setTab("upload")}>
              <UploadCloud size={16} /> Upload
            </button>
            <button className={`tab ${tab === "history" ? "active" : ""}`} onClick={() => setTab("history")}>
              <History size={16} /> History
            </button>
            <button className={`tab ${tab === "records" ? "active" : ""}`} onClick={() => setTab("records")}>
              <Search size={16} /> Records
            </button>
          </nav>
        </header>

        <main>
          {tab === "upload" && <UploadTab onUploadComplete={() => setHistoryKey(k => k + 1)} />}
          {tab === "history" && <HistoryTab key={historyKey} />}
          {tab === "records" && <RecordsTab />}
        </main>
      </div>
    </div>
  );
}