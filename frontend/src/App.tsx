import { useEffect, useState } from "react";
import { Activity, ArrowRight, HeartPulse, ShieldCheck, Stethoscope } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
type ApiState = "checking" | "online" | "offline";

export default function App() {
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/v1/health`)
      .then((response) => {
        if (!response.ok) throw new Error("API health check failed");
        return response.json();
      })
      .then(() => active && setApiState("online"))
      .catch(() => active && setApiState("offline"));
    return () => { active = false; };
  }, []);

  const statusLabel =
    apiState === "online" ? "Connected" :
    apiState === "offline" ? "Unavailable" : "Checking…";

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <a href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight text-emerald-950">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-emerald-700 text-white">
            <HeartPulse size={22} />
          </span>
          MediFlow
        </a>
        <span className="rounded-full border border-emerald-100 bg-white px-3 py-1.5 text-xs font-medium text-emerald-800">
          Pharmacy care, made simpler
        </span>
      </div>

      <section className="mx-auto grid max-w-6xl gap-12 py-16 md:grid-cols-[1.15fr_0.85fr] md:items-center md:py-24">
        <div>
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-800">
            <ShieldCheck size={16} /> Thoughtful, pharmacist-reviewed care
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            Your regular medicines, <span className="text-emerald-700">easier to reorder.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
            A simpler way to manage family refills, submit prescriptions and stay connected with your pharmacy.
          </p>
          <button type="button" disabled className="mt-8 inline-flex cursor-not-allowed items-center gap-2 rounded-xl bg-emerald-800 px-5 py-3 font-semibold text-white opacity-90">
            Customer ordering coming next <ArrowRight size={18} />
          </button>
          <p className="mt-3 text-xs text-slate-500">Day 1 prototype — sign-in and ordering are not enabled yet.</p>
        </div>

        <div className="rounded-3xl border border-emerald-100 bg-white p-7 shadow-sm sm:p-9">
          <div className="mb-7 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-800">
            <Stethoscope size={28} />
          </div>
          <h2 className="text-xl font-semibold text-slate-900">MediFlow system status</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            This panel checks whether the frontend can reach the Day 1 API.
          </p>
          <div className="mt-6 flex items-center justify-between rounded-2xl bg-slate-50 p-4">
            <div className="flex items-center gap-3">
              <Activity className="text-emerald-700" size={20} />
              <span className="text-sm font-medium text-slate-700">Backend API</span>
            </div>
            <span className={`text-sm font-semibold ${
              apiState === "online" ? "text-emerald-700" :
              apiState === "offline" ? "text-rose-600" : "text-amber-600"
            }`}>{statusLabel}</span>
          </div>
          <div className="mt-4 rounded-2xl border border-slate-100 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Next milestone</p>
            <p className="mt-1 text-sm font-medium text-slate-800">Customer sign-in and family profiles</p>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-6xl border-t border-slate-200 py-6 text-xs text-slate-500">
        MediFlow prototype · Do not enter real prescriptions or patient information.
      </footer>
    </main>
  );
}
