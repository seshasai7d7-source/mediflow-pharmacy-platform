
import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ClipboardList,
  FileText,
  RefreshCw,
  UserRound,
} from "lucide-react";
import { Link } from "react-router-dom";

import {
  ApiError,
  pharmacistApi,
  type PharmacistQueueItem,
} from "../lib/api";

export default function PharmacistQueuePage() {
  const [prescriptions, setPrescriptions] = useState<
    PharmacistQueueItem[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await pharmacistApi.getQueue();
      setPrescriptions(data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load the prescription queue.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              to="/dashboard"
              className="text-sm font-medium text-emerald-700 hover:underline"
            >
              ← Back to dashboard
            </Link>

            <h1 className="mt-3 text-3xl font-bold text-slate-900">
              Prescription review queue
            </h1>

            <p className="mt-2 text-slate-600">
              Review customer prescriptions before approving medicine orders.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadQueue()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </header>

        <section className="mb-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-3 text-slate-500">
              <ClipboardList size={20} />
              <span className="text-sm font-medium">
                Awaiting pharmacist review
              </span>
            </div>

            <p className="mt-3 text-3xl font-bold text-slate-900">
              {prescriptions.length}
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-3 text-slate-500">
              <FileText size={20} />
              <span className="text-sm font-medium">
                Queue status
              </span>
            </div>

            <p className="mt-3 text-lg font-semibold text-emerald-700">
              {loading ? "Loading..." : "Up to date"}
            </p>
          </div>
        </section>

        {error && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            <AlertCircle size={20} className="shrink-0" />
            <div>
              <p className="font-semibold">
                Could not load prescriptions
              </p>
              <p className="mt-1">{error}</p>
            </div>
          </div>
        )}

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-5 py-4">
            <h2 className="font-semibold text-slate-900">
              Pending prescriptions
            </h2>
          </div>

          {loading ? (
            <div className="p-10 text-center text-slate-500">
              Loading prescription queue...
            </div>
          ) : prescriptions.length === 0 ? (
            <div className="p-10 text-center">
              <ClipboardList
                size={36}
                className="mx-auto text-slate-300"
              />
              <p className="mt-3 font-semibold text-slate-800">
                No prescriptions awaiting review
              </p>
              <p className="mt-1 text-sm text-slate-500">
                New customer uploads will appear here.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {prescriptions.map((prescription) => (
                <article
                  key={prescription.id}
                  className="flex flex-col justify-between gap-4 p-5 sm:flex-row sm:items-center"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText
                        size={19}
                        className="shrink-0 text-emerald-700"
                      />
                      <h3 className="truncate font-semibold text-slate-900">
                        {prescription.original_filename}
                      </h3>
                    </div>

                    <p className="mt-2 text-sm text-slate-500">
                      Prescription #{prescription.id}
                    </p>

                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-600">
                      <span className="inline-flex items-center gap-1">
                        <UserRound size={15} />
                        {prescription.customer_name ??
                          prescription.customer_email ??
                          `Customer #${prescription.customer_id ?? "Unknown"}`}
                      </span>

                      <span>
                        Uploaded{" "}
                        {new Date(
                          prescription.created_at,
                        ).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-3">
                    <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                      {prescription.status.replace(/_/g, " ")}
                    </span>

                    <Link
                      to={`/pharmacist/prescriptions/${prescription.id}`}
                      className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
                    >
                      Review
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <p className="mt-6 text-xs leading-5 text-slate-500">
          Prescription extraction is a draft only. A qualified pharmacist
          must independently verify the prescription and medicine details
          before approval.
        </p>
      </div>
    </main>
  );
}
