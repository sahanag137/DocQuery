import { useState } from "react";
import "./Login.css";

// Read API base URL from environment configuration
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function Login({ onLogin, onSignupClick, onForgotPassword }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedPassword = password.trim();

    if (!trimmedEmail || !trimmedPassword) {
      setError("Please enter your email address and password.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include", // Enables HttpOnly session cookie handling
        body: JSON.stringify({
          email: trimmedEmail,
          password: password,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        let errorMessage = "Invalid email or password. Please try again.";

        if (response.status === 401) {
          errorMessage = "Incorrect email or password. Please verify your credentials.";
        } else if (response.status === 403) {
          errorMessage = "Your account is currently inactive. Please contact support.";
        } else if (data && data.detail) {
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

      // Persist token and user in localStorage for bearer authentication & session persistence
      if (data?.access_token) {
        localStorage.setItem("docquery_token", data.access_token);
      }
      if (data?.user) {
        localStorage.setItem("docquery_user", JSON.stringify(data.user));
      }

      // Transition to DocQuery dashboard
      onLogin?.(data);
    } catch (err) {
      setError(err.message || "Unable to reach the server. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <div className="login-logo">D</div>
          <h1>DocQuery</h1>
          <p>Your documents, understood.</p>
        </div>

        <div className="login-heading">
          <h2>Welcome back</h2>
          <p>Sign in to continue to your workspace.</p>
        </div>

        {error && (
          <div className="login-error-banner" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            required
          />

          <div className="password-label">
            <label htmlFor="password">Password</label>
            <button
              type="button"
              className="text-button"
              onClick={onForgotPassword}
              disabled={loading}
            >
              Forgot password?
            </button>
          </div>

          <div className="password-input">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              required
            />
            <button
              type="button"
              className="show-password"
              onClick={() => setShowPassword(!showPassword)}
              disabled={loading}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <button type="submit" className="login-button" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="login-footer">
          Don't have an account?{" "}
          <button
            type="button"
            className="text-button"
            onClick={onSignupClick}
            disabled={loading}
          >
            Sign up
          </button>
        </p>
      </section>
    </main>
  );
}

export default Login;
