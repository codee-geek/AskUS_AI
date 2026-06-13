import { useState, useRef, useEffect } from "react";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";
const SESSION_STORAGE_KEY = "rag-session-id";

function getOrCreateSessionId() {
  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;

  const sessionId =
    window.crypto?.randomUUID?.() ||
    `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;

  window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}

// ─────────────────────────────────────────────────────────
// SOURCE CHIP
// ─────────────────────────────────────────────────────────

function SourceChip({ source, onClick }) {
  return (
    <button
      onClick={() => onClick(source)}
      style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        padding: "4px 10px",
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: "20px", color: "#a8b4c8",
        fontSize: "12px", fontFamily: "'DM Mono', monospace",
        cursor: "pointer", transition: "all 0.15s ease", whiteSpace: "nowrap",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = "rgba(255,255,255,0.11)"; e.currentTarget.style.color = "#d4dce8"; }}
      onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.06)"; e.currentTarget.style.color = "#a8b4c8"; }}
    >
      <span style={{ opacity: 0.6 }}>📄</span>
      {source.doc} · p.{source.page}
    </button>
  );
}

// ─────────────────────────────────────────────────────────
// MESSAGE
// ─────────────────────────────────────────────────────────

function Message({ msg, onSourceClick }) {
  const isUser = msg.role === "user";

  const renderText = (text) => {
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**"))
        return <strong key={i} style={{ color: "#e2e8f0", fontWeight: 600 }}>{part.slice(2, -2)}</strong>;
      if (part.startsWith("`") && part.endsWith("`"))
        return <code key={i} style={{ fontFamily: "'DM Mono', monospace", fontSize: "13px", background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: "4px", color: "#93c5fd" }}>{part.slice(1, -1)}</code>;
      if (part.startsWith("*") && part.endsWith("*"))
        return <em key={i} style={{ color: "#cbd5e1" }}>{part.slice(1, -1)}</em>;
      return part;
    });
  };

  return (
    <div style={{
      display: "flex", gap: "12px", padding: "20px 0",
      borderBottom: "1px solid rgba(255,255,255,0.05)",
      animation: "fadeSlideIn 0.3s ease forwards",
    }}>
      {/* Avatar */}
      <div style={{
        width: "32px", height: "32px", borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px",
        background: isUser
          ? "linear-gradient(135deg, #4f8ef7, #7c3aed)"
          : "linear-gradient(135deg, #cf8b5c, #d97757)",
        boxShadow: isUser
          ? "0 0 12px rgba(79,142,247,0.3)"
          : "0 0 12px rgba(207,139,92,0.3)",
      }}>
        {isUser ? "S" : "◆"}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: "13px", fontWeight: 600, marginBottom: "8px",
          color: isUser ? "#93b4f7" : "#cf8b5c",
          fontFamily: "'DM Sans', sans-serif", letterSpacing: "0.01em",
        }}>
          {isUser ? "You" : "RAG Assistant"}
        </div>

        <div style={{ fontSize: "15px", lineHeight: "1.7", color: "#c8d4e0", fontFamily: "'DM Sans', sans-serif", whiteSpace: "pre-wrap" }}>
          {renderText(msg.text)}
        </div>

        {/* Sources */}
        {msg.sources && msg.sources.length > 0 && (
          <div style={{ marginTop: "14px" }}>
            <div style={{
              fontSize: "11px", color: "#5a6a7a", marginBottom: "8px",
              fontFamily: "'DM Mono', monospace", textTransform: "uppercase", letterSpacing: "0.08em",
            }}>
              {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""} retrieved · BM25 + Qdrant hybrid
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {msg.sources.map((s, i) => <SourceChip key={i} source={s} onClick={onSourceClick} />)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// SOURCE MODAL
// ─────────────────────────────────────────────────────────

function SourceModal({ source, onClose }) {
  if (!source) return null;
  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)",
      backdropFilter: "blur(4px)", display: "flex", alignItems: "center",
      justifyContent: "center", zIndex: 100, animation: "fadeIn 0.2s ease",
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: "#1a2230", border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: "16px", padding: "28px", maxWidth: "520px", width: "90%",
        boxShadow: "0 24px 64px rgba(0,0,0,0.5)", animation: "slideUp 0.25s ease",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
          <div>
            <div style={{ fontSize: "13px", color: "#5a7a9a", fontFamily: "'DM Mono', monospace", marginBottom: "4px" }}>
              📄 {source.doc}
            </div>
            <div style={{ fontSize: "12px", color: "#3a5a6a", fontFamily: "'DM Mono', monospace" }}>
              Page {source.page}
            </div>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", color: "#5a6a7a", fontSize: "20px", cursor: "pointer" }}>×</button>
        </div>

        {/* Retrieval method badge */}
        <div style={{ display: "flex", gap: "6px", marginBottom: "14px" }}>
          {["BM25", "Qdrant"].map(label => (
            <span key={label} style={{
              padding: "3px 8px", borderRadius: "6px",
              background: "rgba(207,139,92,0.1)", border: "1px solid rgba(207,139,92,0.2)",
              fontSize: "11px", color: "#cf8b5c", fontFamily: "'DM Mono', monospace",
            }}>{label}</span>
          ))}
        </div>

        <div style={{
          background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
          borderLeft: "3px solid #cf8b5c", borderRadius: "8px", padding: "16px",
          fontSize: "14px", lineHeight: "1.7", color: "#a0b4c4",
          fontFamily: "'DM Sans', sans-serif", fontStyle: "italic",
        }}>
          "{source.snippet}"
        </div>
        <div style={{ marginTop: "16px", fontSize: "12px", color: "#3a4a5a", fontFamily: "'DM Mono', monospace" }}>
          Click outside to close
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// DOC CARD
// ─────────────────────────────────────────────────────────

function DocCard({ doc, onRemove }) {
  const colors = ["#e8d5b7", "#c8d8e8", "#d5e8d4", "#e8d5d5", "#e8e0d5"];
  const color  = colors[doc.name.length % colors.length];

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: "10px",
      padding: "10px 12px", background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", transition: "border-color 0.2s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "rgba(255,255,255,0.16)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)"}
    >
      {/* PDF icon */}
      <div style={{
        width: "32px", height: "38px", background: color, borderRadius: "4px", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "10px", fontWeight: 700, color: "#3a3a3a", fontFamily: "'DM Mono', monospace",
      }}>PDF</div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: "13px", color: "#c8d4e0", fontFamily: "'DM Sans', sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {doc.name}
        </div>

        {doc.uploading && (
          <div style={{ fontSize: "11px", color: "#cf8b5c", fontFamily: "'DM Mono', monospace", marginTop: "2px" }}>
            ⏳ Uploading and indexing with BM25 + Qdrant…
          </div>
        )}
        {!doc.uploading && !doc.error && doc.chunks && (
          <div style={{ fontSize: "11px", color: "#4a6a7a", fontFamily: "'DM Mono', monospace", marginTop: "2px" }}>
            ✅ {doc.chunks} chunks · {doc.pages} pages
          </div>
        )}
        {doc.error && (
          <div style={{ fontSize: "11px", color: "#e87070", fontFamily: "'DM Mono', monospace", marginTop: "2px" }}>
            ❌ {doc.error}
          </div>
        )}
      </div>

      {/* Remove */}
      {!doc.uploading && (
        <button
          onClick={() => onRemove(doc.id)}
          style={{ background: "none", border: "none", color: "#3a5a6a", fontSize: "16px", cursor: "pointer", flexShrink: 0 }}
          onMouseEnter={e => e.currentTarget.style.color = "#e87070"}
          onMouseLeave={e => e.currentTarget.style.color = "#3a5a6a"}
        >×</button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// MAIN APP
// ─────────────────────────────────────────────────────────

export default function RAGChat() {
  const sessionIdRef = useRef(getOrCreateSessionId());
  const [messages, setMessages] = useState([{
    role: "assistant",
    text: "Hello! Upload your PDF documents using the sidebar. I use hybrid retrieval (BM25 + Qdrant) scoped to your session, then answer from the actual document content.",
    sources: [],
  }]);
  const [input,       setInput]       = useState("");
  const [loading,     setLoading]     = useState(false);
  const [docs,        setDocs]        = useState([]);
  const [activeSource,setActiveSource]= useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dragOver,    setDragOver]    = useState(false);
  const [backendOk,   setBackendOk]   = useState(null); // null | true | false
  const [stats,       setStats]       = useState({ docs: 0, chunks: 0 });

  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef= useRef(null);

  // Check backend health on mount
  useEffect(() => {
    fetch(`${API}/`, {
      headers: { "X-Session-ID": sessionIdRef.current },
    })
      .then(r => r.json())
      .then(data => {
        setBackendOk(true);
        setStats({ docs: data.docs_indexed || 0, chunks: data.total_chunks || 0 });
      })
      .catch(() => setBackendOk(false));
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── File upload ───────────────────────────────────────

  const uploadFile = async (file) => {
    const tempId = Date.now() + Math.random();
    setDocs(prev => [...prev, { id: tempId, name: file.name, uploading: true }]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res  = await fetch(`${API}/upload`, {
        method: "POST",
        headers: { "X-Session-ID": sessionIdRef.current },
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      setDocs(prev => prev.map(d =>
        d.id === tempId
          ? { id: tempId, name: file.name, chunks: data.chunks, pages: data.pages, uploading: false }
          : d
      ));
      setStats({
        docs: data.docs_indexed || 0,
        chunks: data.total_chunks || 0,
      });
    } catch (err) {
      setDocs(prev => prev.map(d =>
        d.id === tempId ? { ...d, uploading: false, error: err.message } : d
      ));
    }
  };

  const addFiles = (files) => {
    const pdfs = Array.from(files).filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) { alert("Please upload PDF files only."); return; }
    pdfs.forEach(uploadFile);
  };

  const handleDrop      = (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(false); addFiles(e.dataTransfer.files); };
  const handleDragOver  = (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(true); };
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragOver(false); };
  const handleFileChange= (e) => { addFiles(e.target.files); e.target.value = ""; };
  const removeDoc       = (id) => setDocs(prev => prev.filter(d => d.id !== id));

  // ── Send question ─────────────────────────────────────

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setMessages(prev => [...prev, { role: "user", text: question, sources: [] }]);
    setInput("");
    setLoading(true);

    try {
      const res  = await fetch(`${API}/query`, {
        method:  "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionIdRef.current,
        },
        body:    JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Query failed");

      setMessages(prev => [...prev, {
        role: "assistant",
        text: data.answer,
        sources: data.sources || [],
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: `❌ ${err.message}`,
        sources: [],
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const readyDocs = docs.filter(d => !d.uploading && !d.error);

  // ── Status badge helper ───────────────────────────────
  const statusColor = backendOk === true ? "#48c78e" : backendOk === false ? "#e87070" : "#6a8a9a";
  const statusLabel = backendOk === true ? "Backend Ready" : backendOk === false ? "Backend Offline" : "Checking…";

  // ─────────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #0d1117; }
        @keyframes fadeSlideIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        @keyframes fadeIn      { from { opacity:0; } to { opacity:1; } }
        @keyframes slideUp     { from { opacity:0; transform:translateY(16px) scale(0.97); } to { opacity:1; transform:translateY(0) scale(1); } }
        @keyframes pulse       { 0%,100%{ opacity:.4; transform:scale(.8); } 50%{ opacity:1; transform:scale(1); } }
        @keyframes spin        { from{ transform:rotate(0deg); } to{ transform:rotate(360deg); } }
        textarea:focus { outline:none; }
        textarea       { resize:none; }
        ::-webkit-scrollbar       { width:4px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.08); border-radius:4px; }
      `}</style>

      <div style={{ display:"flex", height:"100vh", background:"#0d1117", fontFamily:"'DM Sans', sans-serif", color:"#c8d4e0", overflow:"hidden" }}>

        {/* ══════════════════ SIDEBAR ══════════════════ */}
        <div style={{
          width: sidebarOpen ? "290px" : "0px", minWidth: sidebarOpen ? "290px" : "0px",
          overflow:"hidden", transition:"all 0.3s cubic-bezier(0.4,0,0.2,1)",
          background:"#111820", borderRight:"1px solid rgba(255,255,255,0.06)", display:"flex", flexDirection:"column",
        }}>
          <div style={{ padding:"20px", flex:1, overflowY:"auto", minWidth:"290px" }}>

            {/* Brand */}
            <div style={{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"28px" }}>
              <div style={{ width:"30px", height:"30px", background:"linear-gradient(135deg,#cf8b5c,#d97757)", borderRadius:"8px", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"14px", boxShadow:"0 4px 12px rgba(207,139,92,0.3)" }}>◆</div>
              <div>
                <div style={{ fontSize:"14px", fontWeight:600, color:"#e2e8f0" }}>DocMind</div>
                <div style={{ fontSize:"11px", color:"#3a5a6a", fontFamily:"'DM Mono', monospace" }}>Hybrid RAG · BM25 + Qdrant</div>
              </div>
            </div>

            {/* Hidden file input */}
            <input ref={fileInputRef} type="file" accept=".pdf" multiple onChange={handleFileChange} style={{ display:"none" }} />

            {/* Drop zone */}
            <div
              onClick={() => fileInputRef.current.click()}
              onDragEnter={handleDragOver} onDragOver={handleDragOver}
              onDragLeave={handleDragLeave} onDrop={handleDrop}
              style={{
                border:`1.5px dashed ${dragOver ? "#cf8b5c" : "rgba(255,255,255,0.1)"}`,
                borderRadius:"12px", padding:"20px", textAlign:"center",
                background: dragOver ? "rgba(207,139,92,0.06)" : "rgba(255,255,255,0.02)",
                cursor:"pointer", transition:"all 0.2s ease", marginBottom:"20px", userSelect:"none",
              }}
            >
              <div style={{ fontSize:"22px", marginBottom:"8px" }}>{dragOver ? "⬇️" : "📂"}</div>
              <div style={{ fontSize:"12px", color:"#5a7a8a", lineHeight:1.6 }}>
                {dragOver
                  ? <span style={{ color:"#cf8b5c" }}>Drop to upload!</span>
                  : <><span>Drop PDFs here</span><br /><span style={{ color:"#3a5a6a" }}>or click to browse</span></>}
              </div>
            </div>

            {/* Stats row */}
            <div style={{ display:"flex", gap:"8px", marginBottom:"14px" }}>
              {[
                { label:"Docs",   value: readyDocs.length },
                { label:"Chunks", value: stats.chunks },
              ].map(s => (
                <div key={s.label} style={{ flex:1, background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:"8px", padding:"8px 10px", textAlign:"center" }}>
                  <div style={{ fontSize:"16px", fontWeight:600, color:"#cf8b5c", fontFamily:"'DM Mono', monospace" }}>{s.value}</div>
                  <div style={{ fontSize:"10px", color:"#3a5a6a", fontFamily:"'DM Mono', monospace", textTransform:"uppercase", letterSpacing:"0.06em" }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Doc list */}
            <div style={{ fontSize:"11px", color:"#3a5a6a", fontFamily:"'DM Mono', monospace", textTransform:"uppercase", letterSpacing:"0.08em", marginBottom:"10px" }}>
              Documents
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
              {docs.map(doc => <DocCard key={doc.id} doc={doc} onRemove={removeDoc} />)}
              {docs.length === 0 && (
                <div style={{ fontSize:"12px", color:"#2a3a4a", textAlign:"center", padding:"20px 0", fontFamily:"'DM Mono', monospace" }}>
                  No documents yet
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ══════════════════ MAIN ══════════════════ */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {/* Top bar */}
          <div style={{ display:"flex", alignItems:"center", padding:"14px 24px", borderBottom:"1px solid rgba(255,255,255,0.06)", background:"#0d1117", gap:"14px" }}>
            <button
              onClick={() => setSidebarOpen(p => !p)}
              style={{ background:"rgba(255,255,255,0.05)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:"8px", padding:"7px 10px", color:"#6a8a9a", cursor:"pointer", fontSize:"14px" }}
              onMouseEnter={e => e.currentTarget.style.background="rgba(255,255,255,0.09)"}
              onMouseLeave={e => e.currentTarget.style.background="rgba(255,255,255,0.05)"}
            >
              {sidebarOpen ? "◀" : "▶"}
            </button>

            <div style={{ flex:1 }}>
              <div style={{ fontSize:"14px", fontWeight:500, color:"#d4dce8" }}>Document Q&A</div>
              <div style={{ fontSize:"12px", color:"#3a5a6a", fontFamily:"'DM Mono', monospace" }}>
                BM25 + Qdrant hybrid retrieval → reranker → GPT-4o
              </div>
            </div>

            {/* Status badge */}
            <div style={{
              display:"flex", alignItems:"center", gap:"6px", padding:"6px 12px",
              background:`${statusColor}14`, border:`1px solid ${statusColor}33`,
              borderRadius:"20px", fontSize:"11px", color: statusColor,
              fontFamily:"'DM Mono', monospace",
            }}>
              <span style={{ width:"6px", height:"6px", borderRadius:"50%", display:"inline-block", background: statusColor, animation: backendOk === true ? "pulse 2s infinite" : "none" }} />
              {statusLabel}
            </div>
          </div>

          {/* Backend offline banner */}
          {backendOk === false && (
            <div style={{ background:"rgba(232,112,112,0.08)", border:"1px solid rgba(232,112,112,0.2)", borderRadius:"10px", margin:"16px 24px 0", padding:"12px 16px", fontSize:"13px", color:"#e87070", fontFamily:"'DM Mono', monospace" }}>
              ⚠️ Backend not running. Open a terminal in the <strong>backend/</strong> folder and run:<br />
              <strong>uvicorn app.main:app --reload</strong>
            </div>
          )}

          {/* Messages */}
          <div style={{ flex:1, overflowY:"auto", padding:"0 24px", maxWidth:"820px", width:"100%", margin:"0 auto" }}>
            {messages.map((msg, i) => <Message key={i} msg={msg} onSourceClick={setActiveSource} />)}

            {/* Typing indicator */}
            {loading && (
              <div style={{ display:"flex", gap:"12px", padding:"20px 0", animation:"fadeSlideIn 0.3s ease" }}>
                <div style={{ width:"32px", height:"32px", borderRadius:"50%", flexShrink:0, background:"linear-gradient(135deg,#cf8b5c,#d97757)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"14px" }}>◆</div>
                <div style={{ paddingTop:"8px" }}>
                  <div style={{ fontSize:"13px", fontWeight:600, color:"#cf8b5c", marginBottom:"10px" }}>RAG Assistant</div>
                  <div style={{ display:"flex", gap:"5px", alignItems:"center" }}>
                    {[0,1,2].map(i => <div key={i} style={{ width:"7px", height:"7px", borderRadius:"50%", background:"#cf8b5c", animation:`pulse 1.2s ease-in-out ${i*0.2}s infinite` }} />)}
                    <span style={{ fontSize:"12px", color:"#4a6a7a", marginLeft:"8px", fontFamily:"'DM Mono', monospace" }}>
                      Running BM25 + Qdrant hybrid retrieval…
                    </span>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div style={{ padding:"16px 24px 24px", maxWidth:"820px", width:"100%", margin:"0 auto" }}>
            <div
              style={{ background:"#151d27", border:"1px solid rgba(255,255,255,0.1)", borderRadius:"16px", padding:"4px 4px 4px 16px", display:"flex", alignItems:"flex-end", gap:"8px", transition:"border-color 0.2s", boxShadow:"0 4px 20px rgba(0,0,0,0.3)" }}
              onFocusCapture={e => e.currentTarget.style.borderColor="rgba(207,139,92,0.4)"}
              onBlurCapture={e  => e.currentTarget.style.borderColor="rgba(255,255,255,0.1)"}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder={readyDocs.length === 0 ? "Upload a PDF first, then ask a question…" : "Ask anything about your documents…"}
                rows={1}
                style={{ flex:1, background:"transparent", border:"none", color:"#d4dce8", fontSize:"14.5px", fontFamily:"'DM Sans', sans-serif", lineHeight:"1.6", padding:"12px 0", maxHeight:"140px", overflowY:"auto" }}
                onInput={e => { e.target.style.height="auto"; e.target.style.height=Math.min(e.target.scrollHeight,140)+"px"; }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                style={{
                  width:"38px", height:"38px", borderRadius:"12px", border:"none",
                  background: input.trim() && !loading ? "linear-gradient(135deg,#cf8b5c,#d97757)" : "rgba(255,255,255,0.06)",
                  color: input.trim() && !loading ? "#fff" : "#3a5a6a",
                  cursor: input.trim() && !loading ? "pointer" : "default",
                  display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px",
                  transition:"all 0.2s ease", flexShrink:0,
                  boxShadow: input.trim() && !loading ? "0 4px 12px rgba(207,139,92,0.3)" : "none",
                }}
              >
                {loading
                  ? <span style={{ width:"14px", height:"14px", border:"2px solid rgba(255,255,255,0.3)", borderTopColor:"#cf8b5c", borderRadius:"50%", animation:"spin 0.8s linear infinite", display:"block" }} />
                  : "↑"}
              </button>
            </div>
            <div style={{ textAlign:"center", fontSize:"11px", color:"#2a3a4a", marginTop:"10px", fontFamily:"'DM Mono', monospace" }}>
              Answers grounded in your documents · Enter to send · Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>

      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />
    </>
  );
}
