
import { useState } from "react";
import "./Signup.css";

function Signup({ onSignup, onBackToLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      alert("Password must contain at least 8 characters.");
      return;
    }

    onSignup?.({ name, email, password });
  };

  return (
    <main className="signup-page">
      <section className="signup-card">
        <div className="signup-brand">
          <div className="signup-logo">D</div>
          <h1>DocQuery</h1>
          <p>Your documents, understood.</p>
        </div>

        <div className="signup-heading">
          <h2>Create your account</h2>
          <p>Get started with your document workspace.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label htmlFor="signup-name">Full name</label>
          <input
            id="signup-name"
            type="text"
            placeholder="Enter your full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <label htmlFor="signup-email">Email address</label>
          <input
            id="signup-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />

          <label htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="Enter your password again"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />

          <button type="submit" className="signup-button">
            Create account
          </button>
        </form>

        <p className="signup-footer">
          Already have an account?{" "}
          <button type="button" onClick={onBackToLogin}>
            Sign in
          </button>
        </p>
      </section>
    </main>
  );
}

export default Signup;
