
import { useState } from "react";
import "./ResetPassword.css";

function ResetPassword({ onReset, onBackToLogin }) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();

    if (password.length < 8) {
      alert("Password must contain at least 8 characters.");
      return;
    }

    if (password !== confirmPassword) {
      alert("Passwords do not match.");
      return;
    }

    onReset?.({ password });
  };

  return (
    <main className="reset-page">
      <section className="reset-card">
        <div className="reset-brand">
          <div className="reset-logo">D</div>
          <h1>DocQuery</h1>
          <p>Your documents, understood.</p>
        </div>

        <h2>Set a new password</h2>
        <p className="reset-description">
          Create a new password for your DocQuery account.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="new-password">New password</label>
          <input
            id="new-password"
            type={showPassword ? "text" : "password"}
            placeholder="Enter new password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
          />

          <label htmlFor="confirm-new-password">Confirm new password</label>
          <input
            id="confirm-new-password"
            type={showPassword ? "text" : "password"}
            placeholder="Confirm new password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />

          <label className="reset-show-password">
            <input
              type="checkbox"
              checked={showPassword}
              onChange={(event) => setShowPassword(event.target.checked)}
            />
            Show password
          </label>

          <button type="submit" className="reset-button">
            Reset password
          </button>
        </form>

        <button
          type="button"
          className="reset-back-button"
          onClick={onBackToLogin}
        >
          ← Back to sign in
        </button>
      </section>
    </main>
  );
}

export default ResetPassword;
