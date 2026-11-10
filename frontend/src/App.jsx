
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
  // AUTHENTICATION
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
  const [resetToken, setResetToken] = useState("");

  // DOCUMENT AND CONVERSATION STATE
  const [file, setFile] = useState(null);
  const [documentId, setDocumentId] = useState("");
  const [conversationId, setConversationId] = useState(null);
  const [attachedDocumentId, setAttachedDocumentId] = useState("");
  const [documents, setDocuments] = useState([]);

  // CHAT STATE
  const [searchTerm, setSearchTerm] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  // LOADING AND UI STATE
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [zoom, setZoom] = useState(100);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // AUTHENTICATION HEADERS
  function getAuthHeaders(extraHeaders = {}) {
    const token = localStorage.getItem("docquery_token");
    const headers = { ...extraHeaders };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  }

  // DISPLAY ERROR MESSAGE FROM API
  function getApiErrorMessage(data, fallback) {
    const detail = data?.detail;

    if (Array.isArray(detail)) {
      return detail
        .map((item) => item.msg || JSON.stringify(item))
        .join(", ");
    }

    return typeof detail === "string" ? detail : fallback;
  }

  // CREATE OR REUSE CONVERSATION AND ATTACH DOCUMENT
  async function getOrCreateConversation(docId) {
    let activeConversationId = conversationId;

    // Create conversation if one does not exist.
    if (!activeConversationId) {
      const createResponse = await fetch(`${API_URL}/chats`, {
        method: "POST",
        headers: getAuthHeaders(),
        credentials: "include",
      });

      const createData = await createResponse.json();

      if (!createResponse.ok) {
        throw new Error(
          typeof createData.detail === "string"
            ? createData.detail
            : "Unable to create a conversation."
        );
      }

      activeConversationId = createData.id;

      if (!activeConversationId) {
        throw new Error("Conversation ID was not returned by the server.");
      }

      setConversationId(activeConversationId);
    }

    // Attach document if it is not already attached.
    if (attachedDocumentId !== String(docId)) {
      const attachResponse = await fetch(
        `${API_URL}/chats/${activeConversationId}/documents`,
        {
          method: "POST",
          headers: getAuthHeaders({
            "Content-Type": "application/json",
          }),
          credentials: "include",
          body: JSON.stringify({
            document_id: String(docId),
          }),
        }
      );

      const attachData = await attachResponse.json();

      if (!attachResponse.ok) {
        throw new Error(
          typeof attachData.detail === "string"
            ? attachData.detail
            : "Unable to attach the document to the conversation."
        );
      }

      setAttachedDocumentId(String(docId));
    }

    return activeConversationId;
  }

  // VERIFY SESSION ON MOUNT
  useEffect(() => {
    async function verifySession() {
      const token = localStorage.getItem("docquery_token");

      try {
        const headers = {};

        if (token) {
          headers.Authorization = `Bearer ${token}`;
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

          localStorage.setItem(
            "docquery_user",
            JSON.stringify(userData)
          );
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

  // LOAD DOCUMENTS AFTER LOGIN
  useEffect(() => {
    if (isLoggedIn) {
      loadDocuments();
    }
  }, [isLoggedIn]);

  // AUTO SCROLL CHAT
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages]);

  // SIGNUP
  function handleSignup() {
    // Signup.jsx handles its own API request.
  }

  // LOGIN
  function handleLogin(data) {
    if (data?.user) {
      setCurrentUser(data.user);
    } else {
      try {
        const stored = localStorage.getItem("docquery_user");
        if (stored) {
          setCurrentUser(JSON.parse(stored));
        }
      } catch {
        // Ignore invalid stored user data.
      }
    }

    setError("");
    setIsLoggedIn(true);
  }

  // LOAD DOCUMENTS
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

      setDocuments(
        Array.isArray(data) ? data : data.documents || []
      );
    } catch (err) {
      console.error("Document loading error:", err);
    } finally {
      setLoadingDocuments(false);
    }
  }

  // FILE VALIDATION
  function handleFileChange(event) {
    const selected = event.target.files?.[0];

    if (!selected) return;

    const allowedExtensions = [
      ".pdf",
      ".txt",
      ".md",
      ".markdown",
    ];

    const hasValidExt = allowedExtensions.some((ext) =>
      selected.name.toLowerCase().endsWith(ext)
    );

    if (
      !hasValidExt &&
      selected.type !== "application/pdf" &&
      selected.type !== "text/plain" &&
      selected.type !== "text/markdown"
    ) {
      setError(
        "Please select a supported document (PDF, TXT, or Markdown)."
      );
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
    setConversationId(null);
    setAttachedDocumentId("");
    setMessages([]);

    event.target.value = "";
  }

  // UPLOAD DOCUMENT
  async function uploadFile(fileToUpload) {
    const targetFile = fileToUpload || file;

    if (!targetFile) {
      setError("Please select a document first.");
      return null;
    }

    console.log(
      "[DocQuery] Starting upload:",
      targetFile.name,
      targetFile.size,
      "bytes"
    );

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", targetFile);

      const token = localStorage.getItem("docquery_token");
      const headers = {};

      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await fetch(
        `${API_URL}/documents/upload`,
        {
          method: "POST",
          headers,
          credentials: "include",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Document upload failed. Please try again."
        );
      }

      const uploadedId = data.document_id || data.id;

      if (!uploadedId) {
        throw new Error(
          "Upload response did not contain a document ID."
        );
      }

      const resolvedId = String(uploadedId);

      setFile(targetFile);
      setDocumentId(resolvedId);
      setConversationId(null);
      setAttachedDocumentId("");
      setMessages([]);

      await loadDocuments();

      console.log(
        "[DocQuery] Upload complete. Document ID:",
        resolvedId
      );

      return resolvedId;
    } catch (err) {
      console.error("[DocQuery] Upload failed:", err);
      setError(err.message || "Unable to upload document.");
      return null;
    } finally {
      setUploading(false);
    }
  }

  // UPLOAD BUTTON HANDLER
  async function handleUpload() {
    await uploadFile(file);
  }

  // ASK QUESTIONS ABOUT THE DOCUMENT
  async function handleAsk(event) {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!documentId) {
      setError(
        "Upload and finish processing a document before asking questions."
      );
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
      // STEP 1: Create conversation and attach document.
      const activeConversationId =
        await getOrCreateConversation(documentId);

      // STEP 2: Query using the INTEGER conversation ID.
      const response = await fetch(
        `${API_URL}/query/${encodeURIComponent(
          activeConversationId
        )}`,
        {
          method: "POST",
          headers: getAuthHeaders({
            "Content-Type": "application/json",
          }),
          credentials: "include",
          body: JSON.stringify({
            question: trimmedQuestion,
            top_k: 10,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(data, "Unable to get an answer.")
        );
      }

      // STEP 3: Display answer and sources.
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
      console.error("[DocQuery] Question error:", err);

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

  // SUMMARIZE THE SELECTED DOCUMENT
  async function handleSummarize() {
    if (!documentId || asking) return;

    setError("");
    setQuestion("");

    const messageId = Date.now();

    setMessages((previous) => [
      ...previous,
      {
        id: messageId,
        question: "Summarize this document",
        answer: "",
        sources: [],
        loading: true,
        isSummary: true,
      },
    ]);

    setAsking(true);

    try {
      // STEP 1: Create conversation and attach document.
      const activeConversationId =
        await getOrCreateConversation(documentId);

      // STEP 2: Call the dedicated summarization endpoint.
      const response = await fetch(
        `${API_URL}/query/${encodeURIComponent(
          activeConversationId
        )}/summarize/${encodeURIComponent(documentId)}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
          credentials: "include",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          getApiErrorMessage(
            data,
            "Unable to summarize the document."
          )
        );
      }

      // STEP 3: Display summary and sources.
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
      console.error("[DocQuery] Summarization error:", err);

      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId
            ? {
                ...message,
                answer: `Unable to summarize the document: ${err.message}`,
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

  // HANDLE SUGGESTION BUTTONS
  function handleSuggestion(suggestion) {
    if (suggestion === "Summarize this document") {
      handleSummarize();
    } else {
      setQuestion(suggestion);
    }
  }

  // SELECT A DOCUMENT
  function selectDocument(document) {
    const id = document.document_id || document.id;

    setDocumentId(String(id));
    setConversationId(null);
    setAttachedDocumentId("");
    setFile(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  // DELETE DOCUMENT
  async function deleteDocument(id) {
    if (
      !window.confirm(
        "Are you sure you want to delete this document?"
      )
    ) {
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

        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to delete document."
        );
      }

      if (String(id) === documentId) {
        setDocumentId("");
        setConversationId(null);
        setAttachedDocumentId("");
        setFile(null);
        setMessages([]);
        setQuestion("");
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
    setConversationId(null);
    setAttachedDocumentId("");
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
      setConversationId(null);
      setAttachedDocumentId("");
      setDocuments([]);
      setSearchTerm("");
      setMessages([]);
      setQuestion("");
      setError("");
      setActiveTab("chat");
    }
  }

  // FILTER DOCUMENTS
  const filteredDocuments = documents.filter((document) => {
    const name =
      document.filename ||
      document.original_filename ||
      "Untitled document";

    return name
      .toLowerCase()
      .includes(searchTerm.trim().toLowerCase());
  });

  const selectedDocument = documents.find(
    (document) =>
      String(document.document_id || document.id) ===
      String(documentId)
  );

  const pdfUrl = file ? URL.createObjectURL(file) : null;

  useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  const authToken = localStorage.getItem("docquery_token");

  const viewUrl = file
    ? `${pdfUrl}#zoom=${zoom}`
    : documentId
    ? `${API_URL}/documents/${encodeURIComponent(
        documentId
      )}/view?token=${encodeURIComponent(
        authToken || ""
      )}#zoom=${zoom}`
    : null;

  // AUTHENTICATION PAGES
  if (checkingAuth) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f3f5ef",
          fontFamily: "'DM Sans', sans-serif",
          color: "#24583d",
        }}
      >
        <p style={{ fontWeight: 600 }}>
          Loading workspace...
        </p>
      </div>
    );
  }

  if (!isLoggedIn) {
    if (authPage === "signup") {
      return (
        <Signup
          onSignup={handleSignup}
          onBackToLogin={() => setAuthPage("login")}
        />
      );
    }

    // FORGOT PASSWORD
    if (authPage === "forgot") {
      return (
        <ForgotPassword
          onBackToLogin={() => setAuthPage("login")}
          onResetPassword={async (email) => {
            try {
              const response = await fetch(
                `${API_URL}/auth/forgot-password`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  credentials: "include",
                  body: JSON.stringify({ email }),
                }
              );

              const data = await response.json();

              if (!response.ok) {
                throw new Error(
                  getApiErrorMessage(
                    data,
                    "Unable to generate reset instructions."
                  )
                );
              }

              if (!data.reset_token) {
                alert(
                  data.message ||
                    "If an account exists with this email, reset instructions have been generated."
                );
                return;
              }

              setResetToken(data.reset_token);
              setAuthPage("reset");

              alert(
                "Reset token generated successfully. Enter your new password."
              );
            } catch (err) {
              alert(
                err.message || "Password reset request failed."
              );
            }
          }}
        />
      );
    }

    // RESET PASSWORD
    if (authPage === "reset") {
      return (
        <ResetPassword
          resetToken={resetToken}
          onBackToLogin={() => setAuthPage("login")}
          onReset={async (passwordData) => {
            try {
              const response = await fetch(
                `${API_URL}/auth/reset-password`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type": "application/json",
                  },
                  credentials: "include",
                  body: JSON.stringify({
                    token: passwordData.token,
                    new_password: passwordData.password,
                  }),
                }
              );

              const data = await response.json();

              if (!response.ok) {
                throw new Error(
                  getApiErrorMessage(
                    data,
                    "Unable to reset your password."
                  )
                );
              }

              alert(
                data.message || "Password reset successfully!"
              );

              setResetToken("");
              setAuthPage("login");
            } catch (err) {
              alert(
                err.message || "Password reset failed."
              );
            }
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
      <aside
        className={`sidebar ${
          sidebarOpen ? "" : "sidebar-closed"
        }`}
      >
        <div className="brand">
          <div className="brand-icon">D</div>

          {sidebarOpen && (
            <div>
              <h2>DocQuery</h2>
              <span>AI DOCUMENT ASSISTANT</span>
            </div>
          )}
        </div>

        <button
          className="new-chat-button"
          onClick={newChat}
        >
          <span>＋</span>
          {sidebarOpen && "New conversation"}
        </button>

        <div className="sidebar-section">
          {sidebarOpen && (
            <p className="sidebar-heading">WORKSPACE</p>
          )}

          <button
            className={`sidebar-link ${
              activeTab === "chat" ? "active" : ""
            }`}
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
            <p className="sidebar-heading">
              RECENT DOCUMENTS
            </p>

            {loadingDocuments && (
              <p className="sidebar-muted">
                Loading documents...
              </p>
            )}

            {!loadingDocuments && documents.length === 0 && (
              <p className="sidebar-muted">
                No documents uploaded yet.
              </p>
            )}

            {documents.map((document) => {
              const id =
                document.document_id || document.id;

              const docName =
                document.filename ||
                document.original_filename ||
                "Untitled document";

              return (
                <button
                  className={`recent-document ${
                    String(id) === String(documentId)
                      ? "selected"
                      : ""
                  }`}
                  key={id}
                  onClick={() => selectDocument(document)}
                  title={docName}
                >
                  <span className="pdf-small">
                    {(
                      document.file_type ||
                      document.mime_type ||
                      "pdf"
                    )
                      .toLowerCase()
                      .includes("pdf")
                      ? "PDF"
                      : "DOC"}
                  </span>

                  <span className="recent-name">
                    {docName}
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
              <strong>
                {currentUser?.full_name || "My Workspace"}
              </strong>
              <span>
                {currentUser?.email || "Personal account"}
              </span>
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

            <span className="breadcrumb">
              Workspace /
            </span>

            <strong>
              {activeTab === "documents"
                ? "Documents"
                : "AI Assistant"}
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
            <button onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}

        {/* Hidden file input */}
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
                <span className="eyebrow">
                  YOUR LIBRARY
                </span>
                <h1>My Documents</h1>
                <p>
                  Manage your uploaded PDF documents.
                </p>
              </div>

              <button
                className="primary-button"
                disabled={uploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading
                  ? "Uploading..."
                  : "＋ Upload PDF"}
              </button>
            </div>

            <div className="document-search">
              <input
                type="text"
                placeholder="Search documents by filename..."
                value={searchTerm}
                onChange={(event) =>
                  setSearchTerm(event.target.value)
                }
              />
            </div>

            <div className="document-grid">
              {filteredDocuments.map((document) => {
                const id =
                  document.document_id || document.id;

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
                  document.upload_date ||
                  document.uploaded_at;

                const docStatus =
                  document.status ||
                  document.processing_status ||
                  "Uploaded";

                return (
                  <div className="document-card" key={id}>
                    <div className="document-card-top">
                      <div className="pdf-icon">
                        {isPdf ? "PDF" : "DOC"}
                      </div>

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
                        ? new Date(
                            docDate
                          ).toLocaleDateString()
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
                <span className="eyebrow">
                  YOUR AI READING SPACE
                </span>

                <h1>Chat with your documents.</h1>

                <p>
                  Upload a PDF, explore its contents and get
                  answers with document references.
                </p>
              </div>
            </div>

            {!documentId && (
              <div className="upload-panel">
                <div className="upload-symbol">↑</div>

                <h2>Start with a document</h2>

                <p>
                  Upload a PDF and let DocQuery help you
                  understand it.
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
                      {file.name
                        .toLowerCase()
                        .endsWith(".pdf")
                        ? "PDF"
                        : "DOC"}
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
                  {(
                    selectedDocument?.file_type ||
                    selectedDocument?.mime_type ||
                    "pdf"
                  )
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

                  <span>
                    Document selected for this conversation
                  </span>
                </div>

                <button
                  className="text-button"
                  onClick={() => {
                    setDocumentId("");
                    setConversationId(null);
                    setAttachedDocumentId("");
                    setFile(null);
                    setMessages([]);
                    setQuestion("");
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
                        setZoom((value) =>
                          Math.max(50, value - 10)
                        )
                      }
                      title="Zoom out"
                    >
                      −
                    </button>

                    <span>{zoom}%</span>

                    <button
                      onClick={() =>
                        setZoom((value) =>
                          Math.min(150, value + 10)
                        )
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
                      <div className="pdf-icon large">
                        ⏳
                      </div>

                      <h3>Uploading document...</h3>

                      <p>
                        Saving and preparing your document for
                        reading.
                      </p>
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
                      <div className="viewer-empty-icon">
                        ▤
                      </div>

                      <h3>
                        Your document will appear here
                      </h3>

                      <p>
                        Upload a PDF or select an existing
                        document to view its contents.
                      </p>
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

                  <span className="ai-label">
                    RAG POWERED
                  </span>
                </div>

                <div className="chat-messages">
                  {messages.length === 0 && (
                    <div className="chat-welcome">
                      <div className="assistant-avatar">
                        ✦
                      </div>

                      <h3>
                        What would you like to know?
                      </h3>

                      <p>
                        Ask questions about your uploaded
                        document. I'll use its content to
                        prepare an answer.
                      </p>

                      <div className="suggestion-list">
                        {[
                          "Summarize this document",
                          "What are the main topics?",
                          "Explain the important findings",
                        ].map((suggestion) => (
                          <button
                            key={suggestion}
                            disabled={!documentId || asking}
                            onClick={() =>
                              handleSuggestion(suggestion)
                            }
                          >
                            {suggestion} <span>↗</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {messages.map((message) => (
                    <div
                      className="conversation"
                      key={message.id}
                    >
                      <div className="user-message">
                        <span className="user-avatar">U</span>
                        <p>{message.question}</p>
                      </div>

                      <div className="assistant-message">
                        <div className="assistant-avatar">
                          ✦
                        </div>

                        <div className="assistant-response">
                          {message.loading ? (
                            <div className="typing">
                              <span></span>
                              <span></span>
                              <span></span>
                              <p>
                                {message.isSummary
                                  ? "Summarizing your entire document..."
                                  : "Reading your document..."}
                              </p>
                            </div>
                          ) : (
                            <>
                              <p className="answer-text">
                                {message.answer}
                              </p>

                              {message.sources?.length > 0 && (
                                <div className="sources">
                                  <strong>
                                    Sources from your document
                                  </strong>

                                  {message.sources.map(
                                    (source, index) => (
                                      <div
                                        className="source-item"
                                        key={`${
                                          source.chunk_id || index
                                        }-${index}`}
                                      >
                                        <span>▤</span>

                                        <div>
                                          <strong>
                                            {source.source ||
                                              "Document source"}
                                          </strong>

                                          <span>
                                            {source.page
                                              ? `Page ${source.page}`
                                              : "Page not provided"}
                                          </span>
                                        </div>
                                      </div>
                                    )
                                  )}
                                </div>
                              )}

                              {!message.failed && (
                                <button
                                  className="copy-button"
                                  onClick={() =>
                                    copyAnswer(message.answer)
                                  }
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

                <form
                  className="chat-input-area"
                  onSubmit={handleAsk}
                >
                  <textarea
                    value={question}
                    onChange={(event) =>
                      setQuestion(event.target.value)
                    }
                    placeholder={
                      documentId
                        ? "Ask anything about your document..."
                        : "Upload a PDF to start asking questions..."
                    }
                    disabled={!documentId || asking}
                    rows={2}
                    onKeyDown={(event) => {
                      if (
                        event.key === "Enter" &&
                        !event.shiftKey
                      ) {
                        event.preventDefault();
                        handleAsk(event);
                      }
                    }}
                  />

                  <div className="input-footer">
                    <span>
                      Answers are based on your document.
                    </span>

                    <button
                      type="submit"
                      disabled={
                        !documentId ||
                        !question.trim() ||
                        asking
                      }
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
