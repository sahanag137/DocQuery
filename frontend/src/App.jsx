
import { useEffect, useRef, useState } from "react";
import "./App.css";
import Login from "./Login";
import Signup from "./Signup";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";

const API_URL = "http://127.0.0.1:8000";

function App() {
  // Always show Login when the application starts.
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authPage, setAuthPage] = useState("login");

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
  const [loggingIn, setLoggingIn] = useState(false);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // AUTHENTICATION HEADERS
  function getAuthHeaders() {
    const token = localStorage.getItem("access_token");

    return token
      ? { Authorization: `Bearer ${token}` }
      : {};
  }

  // LOAD DOCUMENTS AFTER LOGIN
  useEffect(() => {
    if (isLoggedIn) {
      loadDocuments();
    }
  }, [isLoggedIn]);

  // AUTO SCROLL CHAT
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // SIGNUP API
  async function handleSignup(userData) {
    setLoggingIn(true);

    try {
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          full_name: userData.full_name,
          email: userData.email,
          password: userData.password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        let errorMessage = "Unable to create account.";

        if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMessage = data.detail
            .map((item) => item.msg)
            .join(", ");
        }

        throw new Error(errorMessage);
      }

      alert("Account created successfully! Please sign in.");
      setAuthPage("login");
    } catch (err) {
      alert(err.message || "Signup failed. Please try again.");
      throw err;
    } finally {
      setLoggingIn(false);
    }
  }

  // LOGIN API
  async function handleLogin(credentials) {
    setLoggingIn(true);

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Invalid email or password."
        );
      }

      if (!data.access_token) {
        throw new Error("Login response did not contain an access token.");
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user || {}));

      setError("");
      setIsLoggedIn(true);
    } catch (err) {
      alert(err.message || "Unable to login. Please try again.");
    } finally {
      setLoggingIn(false);
    }
  }

  // LOAD DOCUMENTS
  async function loadDocuments() {
    setLoadingDocuments(true);

    try {
      const response = await fetch(`${API_URL}/documents`, {
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("Unable to load documents.");
      }

      const data = await response.json();

      setDocuments(
        Array.isArray(data) ? data : data.documents || []
      );
    } catch (err) {
      console.error("Document loading error:", err);
    } finally {
      setLoadingDocuments(false);
    }
  }

  // PDF FILE VALIDATION
  function handleFileChange(event) {
    const selected = event.target.files?.[0];

    if (!selected) return;

    if (
      selected.type !== "application/pdf" &&
      !selected.name.toLowerCase().endsWith(".pdf")
    ) {
      setError("Please select a valid PDF file.");
      event.target.value = "";
      return;
    }

    if (selected.size > 25 * 1024 * 1024) {
      setError("Please select a PDF smaller than 25 MB.");
      event.target.value = "";
      return;
    }

    setError("");
    setFile(selected);
    setDocumentId("");
    setMessages([]);
  }

  // UPLOAD PDF
  async function handleUpload() {
    if (!file) {
      setError("Please select a PDF first.");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "PDF upload failed. Please try again."
        );
      }

      const uploadedId = data.document_id || data.id;

      if (!uploadedId) {
        throw new Error("Upload response did not contain a document ID.");
      }

      setDocumentId(String(uploadedId));
      await loadDocuments();
    } catch (err) {
      setError(err.message || "Unable to upload PDF.");
    } finally {
      setUploading(false);
    }
  }

  // ASK QUESTIONS ABOUT THE PDF
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
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders(),
          },
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

  // SELECT A DOCUMENT
  function selectDocument(document) {
    const id = document.document_id || document.id;

    setDocumentId(String(id));
    setFile(null);
    setMessages([]);
    setError("");
  }

  // DELETE A DOCUMENT
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

  // CREATE NEW CHAT
  function newChat() {
    setMessages([]);
    setQuestion("");
    setError("");
    setActiveTab("chat");
  }

  // COPY ANSWER
  function copyAnswer(answer) {
    navigator.clipboard.writeText(answer).catch(() => {
      setError("Unable to copy answer.");
    });
  }

  // LOGOUT
  async function handleLogout() {
    const token = localStorage.getItem("access_token");

    try {
      if (token) {
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } catch (err) {
      console.error("Logout request failed:", err);
    }

    localStorage.removeItem("access_token");
    localStorage.removeItem("user");

    setIsLoggedIn(false);
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

  // SEARCH DOCUMENTS
  const filteredDocuments = documents.filter((document) =>
    (document.filename || "Untitled document")
      .toLowerCase()
      .includes(searchTerm.trim().toLowerCase())
  );

  const selectedDocument = documents.find(
    (document) =>
      String(document.document_id || document.id) === documentId
  );

  const pdfUrl = file ? URL.createObjectURL(file) : null;

  useEffect(() => {
    return () => {
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    };
  }, [pdfUrl]);

  // AUTHENTICATION PAGES
  if (!isLoggedIn) {
    if (authPage === "signup") {
      return (
        <Signup
          onSignup={handleSignup}
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

    return (
      <Login
        onLogin={handleLogin}
        onSignupClick={() => setAuthPage("signup")}
        onForgotPassword={() => setAuthPage("forgot")}
      />
    );
  }

  // MAIN DASHBOARD
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

              return (
                <button
                  className={`recent-document ${
                    String(id) === documentId ? "selected" : ""
                  }`}
                  key={id}
                  onClick={() => selectDocument(document)}
                  title={document.filename}
                >
                  <span className="pdf-small">PDF</span>
                  <span className="recent-name">
                    {document.filename || "Untitled document"}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        <div className="sidebar-bottom">
          <div className="profile-avatar">U</div>

          {sidebarOpen && (
            <div className="profile-info">
              <strong>My Workspace</strong>
              <span>Personal account</span>
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
                onClick={() => fileInputRef.current?.click()}
              >
                ＋ Upload PDF
              </button>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              hidden
              onChange={handleFileChange}
            />

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

                return (
                  <div className="document-card" key={id}>
                    <div className="document-card-top">
                      <div className="pdf-icon">PDF</div>

                      <span
                        className={`document-status ${
                          document.status === "indexed" ? "ready" : ""
                        }`}
                      >
                        {document.status || "Uploaded"}
                      </span>
                    </div>

                    <h3>{document.filename}</h3>

                    <p>
                      {document.upload_date
                        ? new Date(document.upload_date).toLocaleDateString()
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
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose a PDF
                </button>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  hidden
                  onChange={handleFileChange}
                />

                {file && (
                  <div className="selected-file">
                    <span className="pdf-icon">PDF</span>

                    <div>
                      <strong>{file.name}</strong>
                      <span>
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                    </div>

                    <button
                      className="text-button"
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
                  PDF files only · Maximum size 25 MB
                </span>
              </div>
            )}

            {documentId && (
              <div className="active-document-bar">
                <div className="pdf-icon">PDF</div>

                <div>
                  <strong>
                    {file?.name ||
                      selectedDocument?.filename ||
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
                  {file && (
                    <iframe
                      title="PDF preview"
                      src={`${pdfUrl}#zoom=${zoom}`}
                      className="pdf-frame"
                    />
                  )}

                  {!file && documentId && (
                    <div className="viewer-empty">
                      <div className="pdf-icon large">PDF</div>
                      <h3>Document is indexed</h3>
                      <p>
                        This document is available for AI questions. Select
                        the original file again to preview it here.
                      </p>
                    </div>
                  )}

                  {!documentId && !file && (
                    <div className="viewer-empty">
                      <div className="viewer-empty-icon">▤</div>
                      <h3>Your PDF will appear here</h3>
                      <p>Upload a document to view its contents.</p>
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
