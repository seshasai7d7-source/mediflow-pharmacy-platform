
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import {
  HeartPulse,
  LockKeyhole,
  Mail,
  Zap,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";

export default function LoginPage() {
  const { login, devLogin, user, loading } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return <div className="grid min-h-screen place-items-center">Loading...</div>;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login({ email: email.trim(), password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDevLogin() {
    setError("");
    setSubmitting(true);

    try {
      await devLogin();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : "Unable to start the demo session. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <Link
          to="/"
          className="mb-8 flex items-center justify-center gap-2 text-2xl font-bold text-emerald-950"
        >
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-700 text-white">
            <HeartPulse size={24} />
          </span>
          MediFlow
        </Link>

        <section className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm sm:p-9">
          <h1 className="text-2xl font-semibold text-slate-900">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Sign in to access your MediFlow account.
          </p>

          {error && (
            <div
              role="alert"
              className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            <div>
              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email address
              </label>
              <div className="flex items-center rounded-xl border border-slate-300 px-3 focus-within:border-emerald-600">
                <Mail size={18} className="text-slate-400" />
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="w-full bg-transparent px-3 py-3 text-sm outline-none"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>
              <div className="flex items-center rounded-xl border border-slate-300 px-3 focus-within:border-emerald-600">
                <LockKeyhole size={18} className="text-slate-400" />
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  className="w-full bg-transparent px-3 py-3 text-sm outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-xl bg-emerald-700 px-4 py-3 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {import.meta.env.DEV && (
            <>
              <div className="my-5 flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-200" />
                <span className="text-xs text-slate-400">OR</span>
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              <button
                type="button"
                onClick={handleDevLogin}
                disabled={submitting}
                className="flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Zap size={18} />
                {submitting ? "Please wait..." : "Quick Login (Demo Customer)"}
              </button>

              <p className="mt-2 text-center text-xs text-slate-400">
                Development use only. Uses a synthetic customer account.
              </p>
            </>
          )}

          <p className="mt-6 text-center text-sm text-slate-600">
            New to MediFlow?{" "}
            <Link
              to="/register"
              className="font-semibold text-emerald-700 hover:underline"
            >
              Create an account
            </Link>
          </p>

          <p className="mt-5 text-center text-xs text-slate-400">
            Pharmacist and administrator accounts must be created by an
            administrator.
          </p>
        </section>
      </div>
    </main>
  );
}
