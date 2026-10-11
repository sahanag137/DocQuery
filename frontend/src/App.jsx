
import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);

  function handleFileChange(event) {
    const selected = event.target.files[0];

    if (selected && selected.type === "application/pdf") {
      setFile(selected);
      setMessages([]);
    } else if (selected) {
      alert("Please select a PDF file.");
      event.target.value = "";
    }
  }

  function handleAsk(event) {
    event.preventDefault();

    if (!file) {
      alert("Please select a PDF first.");
      return;
    }

    if (!question.trim()) return;

    setMessages((previous) => [
      ...previous,
      {
        question: question.trim(),
        answer:
          "The chat interface is ready. Connect the RAG backend to get answers from your PDF.",
      },
    ]);

    setQuestion("");
  }

  return (
    <div className="app">
      <header className="navbar">
        <h2>DocuMind AI</h2>
        <span>AI Document Assistant</span>
      </header>

      <main className="main">
        <div className="tag">YOUR AI READING ASSISTANT</div>
        <h1>Chat with your documents.</h1>
        <p>Upload a PDF and ask questions about its contents.</p>

        <section className="upload-box">
          <div className="file-icon">PDF</div>
          <h2>Upload your document</h2>
          <p>Select a PDF file from your computer.</p>

          <label className="upload-button">
            Choose PDF
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              hidden
            />
          </label>

          {file && (
            <div className="file-details">
              <p>Selected: {file.name}</p>
              <p>Size: {(file.size / 1024 / 1024).toFixed(2)} MB</p>
              <button type="button" onClick={() => setFile(null)}>
                Remove PDF
              </button>
            </div>
          )}
        </section>

        <section className="chat-box">
          <h2>Ask your document</h2>
          <p className="chat-hint">
            {file
              ? "Your PDF is selected. Type a question below."
              : "Select a PDF before asking a question."}
          </p>

          <div className="messages">
            {messages.length === 0 && (
              <p className="empty-chat">
                Example: What are the main points in this document?
              </p>
            )}

            {messages.map((message, index) => (
              <div className="message" key={index}>
                <div className="question">
                  <strong>You</strong>
                  <p>{message.question}</p>
                </div>
                <div className="answer">
                  <strong>DocuMind AI</strong>
                  <p>{message.answer}</p>
                </div>
              </div>
            ))}
          </div>

          <form className="question-form" onSubmit={handleAsk}>
            <input
              type="text"
              placeholder="Ask a question about your PDF..."
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
            <button type="submit">Ask</button>
          </form>
        </section>

        <p className="note">
          Answers will be powered by your document's RAG backend.
        </p>
      </main>
    </div>
  );
}

export default App;