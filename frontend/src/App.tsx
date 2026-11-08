
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  HeartPulse,
  ShieldCheck,
  Stethoscope,
} from "lucide-react";
import {
  Link,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import MyPrescriptionsPage from "./pages/MyPrescriptionsPage";
import PharmacistQueuePage from "./pages/PharmacistQueuePage";
import PharmacistReviewPage from "./pages/PharmacistReviewPage";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

type ApiState = "checking" | "online" | "offline";

function HomePage() {
  const { user, loading } = useAuth();
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    let active = true;

    fetch(`${API_BASE_URL}/api/v1/health`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Health check failed");
        }
        return response.json();
      })
      .then(() => {
        if (active) setApiState("online");
      })
      .catch(() => {
        if (active) setApiState("offline");
      });

    return () => {
      active = false;
    };
  }, []);

  const statusLabel =
    apiState === "online"
      ? "Connected"
      : apiState === "offline"
        ? "Unavailable"
        : "Checking...";

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-2 text-xl font-bold tracking-tight text-emerald-950"
        >
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-emerald-700 text-white">
            <HeartPulse size={22} />
          </span>
          MediFlow
        </Link>

        <div className="flex items-center gap-3">
          {!loading && user ? (
            <Link
              to="/dashboard"
              className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/login"
                className="rounded-xl px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-white"
              >
                Sign in
              </Link>
              <Link
                to="/register"
                className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </header>

      <section className="mx-auto grid max-w-6xl gap-12 py-16 md:grid-cols-[1.15fr_0.85fr] md:items-center md:py-24">
        <div>
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-800">
            <ShieldCheck size={16} />
            Thoughtful, pharmacist-reviewed care
          </p>

          <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            Your regular medicines,{" "}
            <span className="text-emerald-700">
              easier to reorder.
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            A simpler way to manage medicine refills, submit prescriptions,
            and stay connected with your pharmacy.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to={user ? "/dashboard" : "/register"}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-800 px-5 py-3 font-semibold text-white hover:bg-emerald-900"
            >
              {user ? "Go to dashboard" : "Get started"}
              <ArrowRight size={18} />
            </Link>

            {!user && (
              <Link
                to="/login"
                className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50"
              >
                Sign in
              </Link>
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-emerald-100 bg-white p-7 shadow-sm sm:p-9">
          <div className="mb-7 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-800">
            <Stethoscope size={28} />
          </div>

          <h2 className="text-xl font-semibold text-slate-900">
            MediFlow system status
          </h2>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Check whether the frontend can communicate with the backend API.
          </p>

          <div className="mt-6 flex items-center justify-between rounded-2xl bg-slate-50 p-4">
            <div className="flex items-center gap-3">
              <Activity className="text-emerald-700" size={20} />
              <span className="text-sm font-medium text-slate-700">
                Backend API
              </span>
            </div>

            <span
              className={`text-sm font-semibold ${
                apiState === "online"
                  ? "text-emerald-700"
                  : apiState === "offline"
                    ? "text-rose-600"
                    : "text-amber-600"
              }`}
            >
              {statusLabel}
            </span>
          </div>

          <div className="mt-4 rounded-2xl border border-slate-100 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Platform workflow
            </p>
            <p className="mt-1 text-sm font-medium text-slate-800">
              Customer ordering with pharmacist verification
            </p>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl border-t border-slate-200 py-6 text-xs text-slate-500">
        MediFlow prototype · Use synthetic data only. Do not enter real
        prescriptions or patient information.
      </footer>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route
          path="/prescriptions"
          element={<MyPrescriptionsPage />}
        />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={["pharmacist"]} />}>
        <Route
          path="/pharmacist/prescriptions"
          element={<PharmacistQueuePage />}
      />
        <Route
          path="/pharmacist/prescriptions/:id"
          element={<PharmacistReviewPage />}
        />
       </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
