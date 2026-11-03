
import { useState } from "react";
import "./Login.css";

function Login({ onLogin, onSignupClick, onForgotPassword }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!email.trim() || !password.trim()) {
      alert("Please enter your email and password.");
      return;
    }

    onLogin?.({ email, password });
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

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email address</label>

          <input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <div className="password-label">
            <label htmlFor="password">Password</label>

            <button
              type="button"
              className="text-button"
              onClick={onForgotPassword}
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
              required
            />

            <button
              type="button"
              className="show-password"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          <button type="submit" className="login-button">
            Sign in
          </button>
        </form>

        <p className="login-footer">
          Don't have an account?{" "}
          <button
            type="button"
            className="text-button"
            onClick={onSignupClick}
          >
            Sign up
          </button>
        </p>

      </section>
    </main>
  );
}

export default Login;
