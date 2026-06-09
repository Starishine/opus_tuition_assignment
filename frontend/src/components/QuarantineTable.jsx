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

export default function QuarantineTable({ rows }) {
    if (!rows?.length) return null;
    console.log("Rendering QuarantineTable with rows:", rows);
    return (
        <div className="quarantine">
            <h4 className="quarantine-title">
                <FileSpreadsheet className="icon-small" /> Quarantine Log
            </h4>
            <div className="quarantine-box">
                <table className="q-table">
                    <thead>
                        <tr>
                            <th style={{ width: "5%" }}>Row</th>
                            <th style={{ width: "15%" }}>Code</th>
                            <th style={{ width: "35%" }}>Detail</th>
                            <th style={{ width: "45%" }}>Raw Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.map((q, i) => (
                            <tr key={i}>
                                <td>{q.row_number ?? "—"}</td>
                                <td><span className="badge danger">{q.reason_code}</span></td>
                                <td style={{ whiteSpace: "pre-wrap" }}>{q.reason_detail}</td>
                                <td><pre style={{
                                    margin: 0,
                                    padding: "12px",
                                    backgroundColor: "#000000",
                                    borderRadius: "6px",
                                    whiteSpace: "pre-wrap",
                                    wordBreak: "break-word",
                                    maxWidth: "400px",
                                    overflowX: "auto"
                                }}>{JSON.stringify(q.raw_data)}</pre></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}