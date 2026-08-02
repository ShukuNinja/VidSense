import { useState } from "react";
import {
  login,
  register,
  resendOtp,
  verifyOtp,
  finishVerification,
  type AuthVerifyResponse,
} from "../api";
import type { User } from "../types";

type Mode = "login" | "register" | "verify" | "success";

export default function Auth({
  onAuthed,
}: {
  onAuthed: (user: User) => void;
}) {
  const [mode, setMode] = useState<Mode>("login");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");

  const [busy, setBusy] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [verifyResult, setVerifyResult] =
    useState<AuthVerifyResponse | null>(null);

  function reset(next: Mode) {
    setMode(next);

    setError(null);
    setMessage(null);

    setPassword("");
    setOtpCode("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    setBusy(true);
    setError(null);
    setMessage(null);

    try {
      if (mode === "login") {
        const user = await login(email.trim(), password);
        onAuthed(user);
        return;
      }

      if (mode === "register") {
        const result = await register(email.trim(), password);

        setMessage(result.message);

        setPassword("");

        setMode("verify");

        return;
      }

      if (mode === "verify") {
        const result = await verifyOtp(
          email.trim(),
          otpCode.trim()
        );

        setVerifyResult(result);

        setMode("success");

        return;
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err)
      );
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);

    setError(null);

    try {
      const result = await resendOtp(email.trim());

      setMessage(result.message);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : String(err)
      );
    } finally {
      setBusy(false);
    }
  }

  function continueToApp() {
    if (!verifyResult) return;

    const user = finishVerification(verifyResult);

    onAuthed(user);
  }

  if (mode === "success") {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <div className="success-icon">✓</div>

          <h1>Email Verified!</h1>

          <p className="success-message">
            Your account has been created successfully.
          </p>

          <button
            className="auth-submit"
            onClick={continueToApp}
          >
            Continue to VidSense →
          </button>
        </div>
      </div>
    );
  }


  return (
    <div className="auth-screen">
      <div className="auth-card">
        <h1 className="auth-brand">VidSense</h1>

        <p className="auth-sub">
          {mode === "login"
            ? "Sign in to your account"
            : mode === "register"
            ? "Create your account"
            : `Enter the 6-digit code sent to ${email}`}
        </p>

        <form onSubmit={submit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              autoFocus
              disabled={mode === "verify"}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>

          {mode !== "verify" && (
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={
                  mode === "register"
                    ? "At least 6 characters"
                    : "••••••••"
                }
              />
            </label>
          )}

          {mode === "verify" && (
            <label>
              Verification Code
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={otpCode}
                onChange={(e) =>
                  setOtpCode(
                    e.target.value.replace(/\D/g, "")
                  )
                }
                placeholder="Enter 6-digit OTP"
              />
            </label>
          )}

          {error && (
            <p className="form-error">
              {error}
            </p>
          )}

          {message && (
            <p className="form-success">
              {message}
            </p>
          )}

          <button
            type="submit"
            className="auth-submit"
            disabled={
              busy ||
              (mode === "verify" &&
                otpCode.length !== 6)
            }
          >
            {busy
              ? "Please wait..."
              : mode === "login"
              ? "Sign In"
              : mode === "register"
              ? "Create Account"
              : "Verify Email"}
          </button>
        </form>

        {mode === "verify" && (
          <button
            type="button"
            className="auth-secondary"
            onClick={resend}
            disabled={busy}
            style={{ marginTop: 14 }}
          >
            Resend Code
          </button>
        )}

        <p className="auth-toggle">
          {mode === "login"
            ? "No account yet?"
            : mode === "register"
            ? "Already have an account?"
            : "Need another email?"}{" "}

          <button
            type="button"
            onClick={() => {
              if (mode === "verify") {
                reset("login");
              } else {
                reset(
                  mode === "login"
                    ? "register"
                    : "login"
                );
              }
            }}
          >
            {mode === "login"
              ? "Sign Up"
              : mode === "register"
              ? "Sign In"
              : "Back to Sign In"}
          </button>
        </p>
      </div>
    </div>
  );
}