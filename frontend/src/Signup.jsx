import { useState } from "react";
import "./Signup.css";

// Read API base URL from environment or default to local FastAPI server
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function Signup({ onSignup, onBackToLogin }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
<<<<<<< HEAD
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
=======
>>>>>>> 09b71183d2ae901e26f21503c887fbbcafcd028b

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    const trimmedName = name.trim();
    const trimmedEmail = email.trim().toLowerCase();

    // Frontend Validations
    if (!trimmedName) {
      setError("Please enter your full name.");
      return;
    }

    if (!trimmedEmail) {
      setError("Please enter a valid email address.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

<<<<<<< HEAD
    if (!/[A-Za-z]/.test(password)) {
      setError("Password must contain at least one letter.");
      return;
    }

    if (!/\d/.test(password)) {
      setError("Password must contain at least one number.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        body: JSON.stringify({
          full_name: trimmedName,
          email: trimmedEmail,
          password: password,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        let errorMessage = "Registration failed. Please check your information.";

        if (data && data.detail) {
          if (typeof data.detail === "string") {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            errorMessage = data.detail
              .map((err) => err.msg || err.detail || JSON.stringify(err))
              .join(", ");
          }
        }

        throw new Error(errorMessage);
      }

      setSuccess("Account created successfully! Redirecting to sign in...");
      onSignup?.(data);

      // Redirect user to the Login page
      setTimeout(() => {
        onBackToLogin?.();
      }, 1200);
    } catch (err) {
      setError(err.message || "Unable to connect to the server. Please check your network.");
=======
    try {
      setLoading(true);
      await onSignup?.({
        full_name: name.trim(),
        email: email.trim(),
        password,
      });
    } catch (error) {
      alert(error.message || "Signup failed. Please try again.");
>>>>>>> 09b71183d2ae901e26f21503c887fbbcafcd028b
    } finally {
      setLoading(false);
    }
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

        {error && (
          <div className="signup-error-banner" role="alert">
            {error}
          </div>
        )}

        {success && (
          <div className="signup-success-banner" role="status">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label htmlFor="signup-name">Full name</label>
          <input
            id="signup-name"
            type="text"
            placeholder="Enter your full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="signup-email">Email address</label>
          <input
            id="signup-email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="confirm-password">Confirm password</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="Enter your password again"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={loading}
            required
          />

<<<<<<< HEAD
          <button type="submit" className="signup-button" disabled={loading}>
=======
          <button
            type="submit"
            className="signup-button"
            disabled={loading}
          >
>>>>>>> 09b71183d2ae901e26f21503c887fbbcafcd028b
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="signup-footer">
          Already have an account?{" "}
          <button type="button" onClick={onBackToLogin} disabled={loading}>
            Sign in
          </button>
        </p>
      </section>
    </main>
  );
}

export default Signup;
