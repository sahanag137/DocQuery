
import { useEffect, useRef, useState } from "react";
import "./App.css";
import Login from "./Login";
import Signup from "./Signup";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";

const API_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authPage, setAuthPage] = useState("login");
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const stored = localStorage.getItem("docquery_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [checkingAuth, setCheckingAuth] = useState(true);

  function getAuthHeaders(extraHeaders = {}) {
    const token = localStorage.getItem("docquery_token");
    const headers = { ...extraHeaders };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  useEffect(() => {
    async function verifySession() {
      const token = localStorage.getItem("docquery_token");
      try {
        const headers = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const response = await fetch(`${API_URL}/auth/me`, {
          method: "GET",
          headers,
          credentials: "include",
        });

        if (response.ok) {
          const userData = await response.json();
          setCurrentUser(userData);
          setIsLoggedIn(true);
          localStorage.setItem("docquery_user", JSON.stringify(userData));
        } else {
          localStorage.removeItem("docquery_token");
          localStorage.removeItem("docquery_user");
          setIsLoggedIn(false);
          setCurrentUser(null);
        }
      } catch (err) {
        console.error("Session verification error:", err);
      } finally {
        setCheckingAuth(false);
      }
    }

    verifySession();
  }, []);

  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState("");
  const [documents, setDocuments] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [zoom, setZoom] = useState(100);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isLoggedIn) {
      loadDocuments();
    }
  }, [isLoggedIn]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadDocuments() {
    setLoadingDocuments(true);

    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: getAuthHeaders(),
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Unable to load documents.");
      }

      const data = await response.json();
      setDocuments(Array.isArray(data) ? data : data.documents || []);
    } catch (err) {
      console.error("Document loading error:", err);
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function uploadFile(fileToUpload) {
    const targetFile = fileToUpload || file;
    if (!targetFile) {
      setError("Please select a document first.");
      return null;
    }

    console.log("[DocQuery] Starting upload:", targetFile.name, targetFile.size, "bytes");
    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", targetFile);

      const token = localStorage.getItem("docquery_token");
      const headers = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      console.log("[DocQuery] POST", `${API_URL}/documents/upload`, "token present:", !!token);

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        headers,
        credentials: "include",
        body: formData,
      });

      console.log("[DocQuery] Upload response status:", response.status);

      const data = await response.json();
      console.log("[DocQuery] Upload response data:", data);

      if (!response.ok) {
        throw new Error(
          data.detail || "Document upload failed. Please try again."
        );
      }

      const uploadedId = data.document_id || data.id;

      if (!uploadedId) {
        throw new Error("Upload response did not contain a document ID.");
      }

      const resolvedId = String(uploadedId);
      setFile(targetFile);
      setDocumentId(resolvedId);
      await loadDocuments();
      console.log("[DocQuery] Upload complete. Document ID:", resolvedId);
      return resolvedId;
    } catch (err) {
      console.error("[DocQuery] Upload failed:", err);
      setError(err.message || "Unable to upload document.");
      return null;
    } finally {
      setUploading(false);
    }
  }

  async function handleFileChange(event) {
    const selected = event.target.files?.[0];

    if (!selected) return;

    const allowedExtensions = [".pdf", ".txt", ".md", ".markdown"];
    const hasValidExt = allowedExtensions.some((ext) =>
      selected.name.toLowerCase().endsWith(ext)
    );

    if (
      !hasValidExt &&
      selected.type !== "application/pdf" &&
      selected.type !== "text/plain" &&
      selected.type !== "text/markdown"
    ) {
      setError("Please select a supported document (PDF, TXT, or Markdown).");
      event.target.value = "";
      return;
    }

    if (selected.size > 25 * 1024 * 1024) {
      setError("Please select a file smaller than 25 MB.");
      event.target.value = "";
      return;
    }

    setError("");
    setFile(selected);
    setDocumentId("");
    setMessages([]);

    // Automatically upload upon file selection
    await uploadFile(selected);
    event.target.value = "";
  }

  async function handleUpload() {
    await uploadFile(file);
  }

  async function handleAsk(event) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!documentId) {
      setError("Upload and finish processing a PDF before asking questions.");
      return;
    }

    if (!trimmedQuestion || asking) return;

    setError("");
    setQuestion("");

    const messageId = Date.now();

    setMessages((previous) => [
      ...previous,
      {
        id: messageId,
        question: trimmedQuestion,
        answer: "",
        sources: [],
        loading: true,
      },
    ]);

    setAsking(true);

    try {
      const response = await fetch(
        `${API_URL}/query/${encodeURIComponent(documentId)}`,
        {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          credentials: "include",
          body: JSON.stringify({
            question: trimmedQuestion,
            top_k: 5,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to get an answer.");
      }

      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId
            ? {
                ...message,
                answer: data.answer,
                sources: data.sources || [],
                loading: false,
              }
            : message
        )
      );
    } catch (err) {
      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId
            ? {
                ...message,
                answer: `Unable to get an answer: ${err.message}`,
                loading: false,
                failed: true,
              }
            : message
        )
      );
    } finally {
      setAsking(false);
    }
  }

  function selectDocument(document) {
    const id = document.document_id || document.id;

    setDocumentId(String(id));
    setFile(null);
    setMessages([]);
    setError("");
  }

  async function deleteDocument(id) {
    if (!window.confirm("Are you sure you want to delete this document?")) {
      return;
    }

    try {
      const response = await fetch(
        `${API_URL}/documents/${encodeURIComponent(id)}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
          credentials: "include",
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Unable to delete document.");
      }

      if (String(id) === documentId) {
        setDocumentId("");
        setFile(null);
        setMessages([]);
      }

      await loadDocuments();
    } catch (err) {
      setError(err.message);
    }
  }

  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
    setActiveTab("chat");
  }

  function copyAnswer(answer) {
    navigator.clipboard.writeText(answer).catch(() => {
      setError("Unable to copy answer.");
    });
  }

  async function handleLogout() {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
      });
    } catch (err) {
      console.warn("Logout error:", err);
    } finally {
      localStorage.removeItem("docquery_token");
      localStorage.removeItem("docquery_user");
      setIsLoggedIn(false);
      setCurrentUser(null);
      setAuthPage("login");
      setFile(null);
      setDocumentId("");
      setDocuments([]);
      setSearchTerm("");
      setMessages([]);
      setQuestion("");
      setError("");
      setActiveTab("chat");
    }
  }

  const filteredDocuments = documents.filter((document) => {
    const name =
      document.filename || document.original_filename || "Untitled document";
    return name.toLowerCase().includes(searchTerm.trim().toLowerCase());
  });

  const selectedDocument = documents.find(
    (document) =>
      String(document.document_id || document.id) === String(documentId)
  );

  const pdfUrl = file ? URL.createObjectURL(file) : null;

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  const authToken = localStorage.getItem("docquery_token");
  const viewUrl = file
    ? `${pdfUrl}#zoom=${zoom}`
    : documentId
    ? `${API_URL}/documents/${encodeURIComponent(documentId)}/view?token=${encodeURIComponent(authToken || "")}#zoom=${zoom}`
    : null;

  // Authentication pages
  if (!isLoggedIn) {
    if (authPage === "signup") {
      return (
        <Signup
          onSignup={(userData) => {
            console.log("Signup form submitted:", userData);
            // User registered successfully
          }}
          onBackToLogin={() => setAuthPage("login")}
        />
      );
    }

    if (authPage === "forgot") {
      return (
        <ForgotPassword
          onBackToLogin={() => setAuthPage("login")}
          onResetPassword={(email) => {
            console.log("Password reset requested for:", email);
            alert(
              "Password reset API connection is pending. Opening the reset page for frontend testing."
            );
            setAuthPage("reset");
          }}
        />
      );
    }

    if (authPage === "reset") {
      return (
        <ResetPassword
          onBackToLogin={() => setAuthPage("login")}
          onReset={(passwordData) => {
            console.log("New password submitted:", passwordData);
            alert("Reset Password API connection is pending.");
            setAuthPage("login");
          }}
        />
      );
    }

    if (checkingAuth) {
      return (
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#f3f5ef", fontFamily: "'DM Sans', sans-serif", color: "#24583d" }}>
          <p style={{ fontWeight: 600 }}>Loading workspace...</p>
        </div>
      );
    }

    return (
      <Login
        onLogin={(authData) => {
          setIsLoggedIn(true);
          if (authData?.user) {
            setCurrentUser(authData.user);
          }
        }}
        onSignupClick={() => setAuthPage("signup")}
        onForgotPassword={() => setAuthPage("forgot")}
      />
    );
  }

  // Main dashboard
  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "" : "sidebar-closed"}`}>
        <div className="brand">
          <div className="brand-icon">D</div>
          {sidebarOpen && (
            <div>
              <h2>DocQuery</h2>
              <span>AI DOCUMENT ASSISTANT</span>
            </div>
          )}
        </div>

        <button className="new-chat-button" onClick={newChat}>
          <span>＋</span>
          {sidebarOpen && "New conversation"}
        </button>

        <div className="sidebar-section">
          {sidebarOpen && <p className="sidebar-heading">WORKSPACE</p>}

          <button
            className={`sidebar-link ${activeTab === "chat" ? "active" : ""}`}
            onClick={() => setActiveTab("chat")}
          >
            <span>◫</span>
            {sidebarOpen && "AI Chat"}
          </button>

          <button
            className={`sidebar-link ${
              activeTab === "documents" ? "active" : ""
            }`}
            onClick={() => setActiveTab("documents")}
          >
            <span>▤</span>
            {sidebarOpen && "My Documents"}
          </button>
        </div>

        {sidebarOpen && (
          <div className="sidebar-section recent-section">
            <p className="sidebar-heading">RECENT DOCUMENTS</p>

            {loadingDocuments && (
              <p className="sidebar-muted">Loading documents...</p>
            )}

            {!loadingDocuments && documents.length === 0 && (
              <p className="sidebar-muted">No documents uploaded yet.</p>
            )}

            {documents.map((document) => {
              const id = document.document_id || document.id;
              const docName =
                document.filename ||
                document.original_filename ||
                "Untitled document";

              return (
                <button
                  className={`recent-document ${
                    String(id) === String(documentId) ? "selected" : ""
                  }`}
                  key={id}
                  onClick={() => selectDocument(document)}
                  title={docName}
                >
                  <span className="pdf-small">
                    {(document.file_type || document.mime_type || "pdf")
                      .toLowerCase()
                      .includes("pdf")
                      ? "PDF"
                      : "DOC"}
                  </span>
                  <span className="recent-name">{docName}</span>
                </button>
              );
            })}
          </div>
        )}

        <div className="sidebar-bottom">
          <div className="profile-avatar">U</div>

          {sidebarOpen && (
            <div className="profile-info">
              <strong>{currentUser?.full_name || "My Workspace"}</strong>
              <span>{currentUser?.email || "Personal account"}</span>
            </div>
          )}

          <button
            className="icon-button"
            onClick={handleLogout}
            title="Logout"
          >
            ↪
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              title="Toggle sidebar"
            >
              ☰
            </button>

            <span className="breadcrumb">Workspace / </span>

            <strong>
              {activeTab === "documents" ? "Documents" : "AI Assistant"}
            </strong>
          </div>

          <div className="topbar-right">
            <span className="status-indicator"></span>
            <span>Document workspace</span>
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={() => setError("")}>×</button>
          </div>
        )}

        {/* Hidden file input — always in DOM so both tabs can trigger it */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
          hidden
          onChange={handleFileChange}
        />

        {activeTab === "documents" ? (
          <section className="documents-page">
            <div className="page-heading">
              <div>
                <span className="eyebrow">YOUR LIBRARY</span>
                <h1>My Documents</h1>
                <p>Manage your uploaded PDF documents.</p>
              </div>

              <button
                className="primary-button"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? "Uploading..." : "＋ Upload PDF"}
              </button>
            </div>

            <div className="document-search">
              <input
                type="text"
                placeholder="Search documents by filename..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
              />
            </div>

            <div className="document-grid">
              {filteredDocuments.map((document) => {
                const id = document.document_id || document.id;
                const docName =
                  document.filename ||
                  document.original_filename ||
                  "Untitled document";
                const isPdf = (
                  document.file_type ||
                  document.mime_type ||
                  "pdf"
                )
                  .toLowerCase()
                  .includes("pdf");
                const docDate =
                  document.upload_date || document.uploaded_at;
                const docStatus =
                  document.status ||
                  document.processing_status ||
                  "Uploaded";

                return (
                  <div className="document-card" key={id}>
                    <div className="document-card-top">
                      <div className="pdf-icon">{isPdf ? "PDF" : "DOC"}</div>

                      <span
                        className={`document-status ${
                          docStatus === "indexed" ? "ready" : ""
                        }`}
                      >
                        {docStatus}
                      </span>
                    </div>

                    <h3>{docName}</h3>

                    <p>
                      {docDate
                        ? new Date(docDate).toLocaleDateString()
                        : "Date unavailable"}
                    </p>

                    <div className="document-card-actions">
                      <button
                        onClick={() => {
                          selectDocument(document);
                          setActiveTab("chat");
                        }}
                      >
                        Open document
                      </button>

                      <button
                        className="delete-button"
                        onClick={() => deleteDocument(id)}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}

              {filteredDocuments.length === 0 && (
                <div className="empty-documents">
                  <div>▤</div>
                  <h3>
                    {documents.length === 0
                      ? "Your library is empty"
                      : "No matching documents found"}
                  </h3>
                  <p>
                    {documents.length === 0
                      ? "Upload your first PDF to get started."
                      : "Try searching with a different filename."}
                  </p>
                </div>
              )}
            </div>
          </section>
        ) : (
          <section className="workspace">
            <div className="workspace-heading">
              <div>
                <span className="eyebrow">YOUR AI READING SPACE</span>
                <h1>Chat with your documents.</h1>
                <p>
                  Upload a PDF, explore its contents and get answers with
                  document references.
                </p>
              </div>
            </div>

            {!documentId && (
              <div className="upload-panel">
                <div className="upload-symbol">↑</div>
                <h2>Start with a document</h2>
                <p>
                  Upload a PDF and let DocQuery help you understand it.
                </p>

                <button
                  className="primary-button"
                  disabled={uploading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {uploading ? "Uploading..." : "Choose a PDF"}
                </button>

                {file && (
                  <div className="selected-file">
                    <span className="pdf-icon">
                      {file.name.toLowerCase().endsWith(".pdf") ? "PDF" : "DOC"}
                    </span>

                    <div>
                      <strong>{file.name}</strong>
                      <span>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>

                    <button
                      className="text-button"
                      disabled={uploading}
                      onClick={() => {
                        setFile(null);
                        setError("");
                      }}
                    >
                      Remove
                    </button>
                  </div>
                )}

                {file && (
                  <button
                    className="primary-button upload-submit"
                    disabled={uploading}
                    onClick={handleUpload}
                  >
                    {uploading
                      ? "Uploading and indexing..."
                      : "Upload and process PDF"}
                  </button>
                )}

                <span className="upload-note">
                  PDF, TXT, or Markdown · Maximum size 25 MB
                </span>
              </div>
            )}

            {documentId && (
              <div className="active-document-bar">
                <div className="pdf-icon">
                  {(selectedDocument?.file_type || selectedDocument?.mime_type || "pdf")
                    .toLowerCase()
                    .includes("pdf")
                    ? "PDF"
                    : "DOC"}
                </div>

                <div>
                  <strong>
                    {file?.name ||
                      selectedDocument?.filename ||
                      selectedDocument?.original_filename ||
                      "Selected document"}
                  </strong>

                  <span>Document selected for this conversation</span>
                </div>

                <button
                  className="text-button"
                  onClick={() => {
                    setDocumentId("");
                    setFile(null);
                    setMessages([]);
                    setError("");
                  }}
                >
                  Change document
                </button>
              </div>
            )}

            <div className="work-panels">
              <section className="viewer-panel">
                <div className="panel-heading">
                  <div>
                    <span className="panel-icon">▤</span>
                    <strong>Document viewer</strong>
                  </div>

                  <div className="viewer-tools">
                    <button
                      onClick={() =>
                        setZoom((value) => Math.max(50, value - 10))
                      }
                      title="Zoom out"
                    >
                      −
                    </button>

                    <span>{zoom}%</span>

                    <button
                      onClick={() =>
                        setZoom((value) => Math.min(150, value + 10))
                      }
                      title="Zoom in"
                    >
                      +
                    </button>
                  </div>
                </div>

                <div className="viewer-content">
                  {uploading && (
                    <div className="viewer-empty">
                      <div className="pdf-icon large">⏳</div>
                      <h3>Uploading document...</h3>
                      <p>Saving and preparing your document for reading.</p>
                    </div>
                  )}

                  {!uploading && viewUrl && (
                    <iframe
                      key={`${documentId || "local"}-${zoom}`}
                      title="Document preview"
                      src={viewUrl}
                      className="pdf-frame"
                    />
                  )}

                  {!uploading && !viewUrl && (
                    <div className="viewer-empty">
                      <div className="viewer-empty-icon">▤</div>
                      <h3>Your document will appear here</h3>
                      <p>Upload a PDF or select an existing document to view its contents.</p>
                    </div>
                  )}
                </div>
              </section>

              <section className="chat-panel">
                <div className="panel-heading">
                  <div>
                    <span className="panel-icon">✦</span>
                    <strong>AI Assistant</strong>
                  </div>

                  <span className="ai-label">RAG POWERED</span>
                </div>

                <div className="chat-messages">
                  {messages.length === 0 && (
                    <div className="chat-welcome">
                      <div className="assistant-avatar">✦</div>
                      <h3>What would you like to know?</h3>

                      <p>
                        Ask questions about your uploaded document. I'll use
                        its content to prepare an answer.
                      </p>

                      <div className="suggestion-list">
                        {[
                          "Summarize this document",
                          "What are the main topics?",
                          "Explain the important findings",
                        ].map((suggestion) => (
                          <button
                            key={suggestion}
                            disabled={!documentId}
                            onClick={() => setQuestion(suggestion)}
                          >
                            {suggestion} <span>↗</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {messages.map((message) => (
                    <div className="conversation" key={message.id}>
                      <div className="user-message">
                        <span className="user-avatar">U</span>
                        <p>{message.question}</p>
                      </div>

                      <div className="assistant-message">
                        <div className="assistant-avatar">✦</div>

                        <div className="assistant-response">
                          {message.loading ? (
                            <div className="typing">
                              <span></span>
                              <span></span>
                              <span></span>
                              <p>Reading your document...</p>
                            </div>
                          ) : (
                            <>
                              <p className="answer-text">{message.answer}</p>

                              {message.sources?.length > 0 && (
                                <div className="sources">
                                  <strong>Sources from your document</strong>

                                  {message.sources.map((source, index) => (
                                    <div
                                      className="source-item"
                                      key={`${source.chunk_id || index}-${index}`}
                                    >
                                      <span>▤</span>

                                      <div>
                                        <strong>
                                          {source.source || "Document source"}
                                        </strong>

                                        <span>
                                          {source.page
                                            ? `Page ${source.page}`
                                            : "Page not provided"}
                                        </span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {!message.failed && (
                                <button
                                  className="copy-button"
                                  onClick={() => copyAnswer(message.answer)}
                                >
                                  Copy answer
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  <div ref={messagesEndRef}></div>
                </div>

                <form className="chat-input-area" onSubmit={handleAsk}>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder={
                      documentId
                        ? "Ask anything about your document..."
                        : "Upload a PDF to start asking questions..."
                    }
                    disabled={!documentId || asking}
                    rows={2}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.shiftKey) {
                        event.preventDefault();
                        handleAsk(event);
                      }
                    }}
                  />

                  <div className="input-footer">
                    <span>Answers are based on your document.</span>

                    <button
                      type="submit"
                      disabled={!documentId || !question.trim() || asking}
                    >
                      {asking ? "..." : "↑"}
                    </button>
                  </div>
                </form>
              </section>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
