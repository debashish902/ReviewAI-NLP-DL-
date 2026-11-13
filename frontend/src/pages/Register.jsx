import React, { useState } from "react";
import { API_URL } from "../config/api";

function Register({ onRegister, onBackToLogin, theme, toggleTheme }) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Password requirements
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    symbol: /[^A-Za-z0-9]/.test(password),
  };

  const isPasswordStrong = Object.values(passwordChecks).every(Boolean);

  const handleRegister = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    if (!username || !email || !password) {
      setError("All fields are required");
      return;
    }

    // Don't allow registration with a weak password
    if (!isPasswordStrong) {
      setError("Please meet all password requirements.");
      return;
    }

    try {
      setLoading(true);

      const response = await fetch(
        `${API_URL}/api/auth/register`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username,
            email,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || "Registration failed");
      }

      setSuccess("Registration successful! You can now login.");

      setUsername("");
      setEmail("");
      setPassword("");

      setTimeout(() => {
        onRegister();
      }, 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page">
      <button className="theme-toggle" onClick={toggleTheme} style={{ position: 'absolute', top: '20px', right: '20px' }} title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
      <div className="register-card">

        <div className="register-logo">🤖</div>

        <h1>SmartReview AI</h1>

        <p className="register-subtitle">
          AI-Powered E-Commerce Review Analysis
        </p>

        <h2>Create Account</h2>

        <p className="register-description">
          Create your account to manage product reviews.
        </p>

        <form onSubmit={handleRegister}>

          <label>Username</label>

          <input
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <label>Email</label>

          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label>Password</label>

          <div className="register-password-wrapper">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <button
              type="button"
              className="register-eye-button"
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "🙈" : "👁️"}
            </button>
          </div>

          {/* Password Requirements */}
          {password && (
            <div className="password-requirements">

              <p className="password-title">
                Password must contain:
              </p>

              <p className={passwordChecks.length ? "valid" : "invalid"}>
                {passwordChecks.length ? "✓" : "✕"} At least 8 characters
              </p>

              <p className={passwordChecks.uppercase ? "valid" : "invalid"}>
                {passwordChecks.uppercase ? "✓" : "✕"} One uppercase letter
              </p>

              <p className={passwordChecks.lowercase ? "valid" : "invalid"}>
                {passwordChecks.lowercase ? "✓" : "✕"} One lowercase letter
              </p>

              <p className={passwordChecks.number ? "valid" : "invalid"}>
                {passwordChecks.number ? "✓" : "✕"} One number
              </p>

              <p className={passwordChecks.symbol ? "valid" : "invalid"}>
                {passwordChecks.symbol ? "✓" : "✕"} One symbol
              </p>

              {isPasswordStrong && (
                <p className="password-strong">
                  ✓ Strong password
                </p>
              )}

            </div>
          )}

          {error && (
            <div className="register-error">
              {error}
            </div>
          )}

          {success && (
            <div className="register-success">
              {success}
            </div>
          )}

          <button
            type="submit"
            className="register-button"
            disabled={loading}
          >
            {loading ? "Creating Account..." : "Create Account"}
          </button>

        </form>

        <p className="register-switch">
          Already have an account?

          <button
            type="button"
            className="register-link"
            onClick={onBackToLogin}
          >
            Back to Login
          </button>
        </p>

      </div>
    </div>
  );
}

export default Register;