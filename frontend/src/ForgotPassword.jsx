
import { useState } from "react";
import "./ForgotPassword.css";

function ForgotPassword({ onBackToLogin, onResetPassword }) {
  const [email, setEmail] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!email.trim()) {
      alert("Please enter your email address.");
      return;
    }

    onResetPassword?.(email);
  };

  return (
    <main className="forgot-page">
      <section className="forgot-card">
        <div className="forgot-brand">
          <div className="forgot-logo">D</div>
          <h1>DocQuery</h1>
          <p>Your documents, understood.</p>
        </div>

        <div className="forgot-icon">✉</div>

        <h2>Forgot your password?</h2>
        <p className="forgot-description">
          Enter your registered email address. We'll help you reset your
          password.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="forgot-email">Email address</label>

          <input
            id="forgot-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <button type="submit" className="forgot-button">
            Send reset instructions
          </button>
        </form>

        <button
          type="button"
          className="back-login-button"
          onClick={onBackToLogin}
        >
          ← Back to sign in
        </button>
      </section>
    </main>
  );
}

export default ForgotPassword;
