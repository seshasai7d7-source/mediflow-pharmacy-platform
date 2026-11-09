
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  Clock,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  prescriptionApi,
  refillApi,
  type Prescription,
  type RefillPlan,
  type RefillRequest,
} from "../lib/api";

const planStatusStyles: Record<string, string> = {
  pending_review: "bg-amber-100 text-amber-800",
  active: "bg-emerald-100 text-emerald-800",
  paused: "bg-slate-100 text-slate-700",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-slate-100 text-slate-600",
};

const requestStatusStyles: Record<string, string> = {
  pending_review: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  cancelled: "bg-slate-100 text-slate-600",
};

function formatDate(value: string | null) {
  if (!value) return "Not scheduled";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not scheduled";

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function StatusBadge({ status }: { status: string }) {
  const style =
    planStatusStyles[status] ??
    requestStatusStyles[status] ??
    "bg-slate-100 text-slate-700";

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${style}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function CustomerRefillsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [plans, setPlans] = useState<RefillPlan[]>([]);
  const [requests, setRequests] = useState<RefillRequest[]>([]);

  const [prescriptionId, setPrescriptionId] = useState("");
  const [intervalDays, setIntervalDays] = useState("30");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [prescriptionData, planData, requestData] = await Promise.all([
        prescriptionApi.getMyPrescriptions(),
        refillApi.getMyPlans(),
        refillApi.getMyRequests(),
      ]);

      setPrescriptions(prescriptionData);
      setPlans(planData);
      setRequests(requestData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load refill information.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const approvedPrescriptions = prescriptions.filter(
    (prescription) => prescription.status === "approved",
  );

  async function handleCreatePlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!prescriptionId) {
      setError("Please select an approved prescription.");
      return;
    }

    const days = Number(intervalDays);
    if (!Number.isInteger(days) || days < 1 || days > 365) {
      setError("The refill interval must be between 1 and 365 days.");
      return;
    }

    setCreating(true);

    try {
      await refillApi.createPlan({
        prescription_id: Number(prescriptionId),
        interval_days: days,
      });

      setPrescriptionId("");
      setIntervalDays("30");
      setSuccess("Refill plan submitted for pharmacist review.");
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create refill plan.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function handlePlanStatus(
    planId: number,
    newStatus: "paused" | "active" | "cancelled",
  ) {
    setError("");
    setSuccess("");
    setActionId(planId);

    try {
      await refillApi.updatePlanStatus(planId, newStatus);
      setSuccess(`Refill plan ${newStatus} successfully.`);
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to update refill plan.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleCreateRequest(planId: number) {
    setError("");
    setSuccess("");
    setActionId(planId);

    try {
      await refillApi.createRequest(planId);
      setSuccess("Refill request submitted for pharmacist review.");
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to submit refill request.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-8">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link
              to="/dashboard"
              className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-emerald-700"
            >
              <ArrowLeft size={16} />
              Back to dashboard
            </Link>

            <h1 className="text-3xl font-bold tracking-tight text-slate-900">
              Refill Management
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Manage your prescription refill plans and requests.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadData()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        {success && (
          <div
            role="status"
            className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
          >
            {success}
          </div>
        )}

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-xl bg-emerald-100 p-3 text-emerald-700">
              <Plus size={21} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Create a refill plan
              </h2>
              <p className="text-sm text-slate-500">
                Submit an approved prescription for pharmacist review.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleCreatePlan}
            className="grid gap-4 sm:grid-cols-[1fr_180px_auto] sm:items-end"
          >
            <div>
              <label
                htmlFor="prescription"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Approved prescription
              </label>
              <select
                id="prescription"
                value={prescriptionId}
                onChange={(event) => setPrescriptionId(event.target.value)}
                disabled={creating || loading}
                required
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <option value="">Select a prescription</option>
                {approvedPrescriptions.map((prescription) => (
                  <option
                    key={prescription.id}
                    value={prescription.id}
                  >
                    Prescription #{prescription.id} —{" "}
                    {prescription.original_filename}
                  </option>
                ))}
              </select>
              {approvedPrescriptions.length === 0 && !loading && (
                <p className="mt-2 text-xs text-amber-700">
                  You need an approved prescription before creating a refill
                  plan.
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="interval"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Interval (days)
              </label>
              <input
                id="interval"
                type="number"
                min="1"
                max="365"
                value={intervalDays}
                onChange={(event) => setIntervalDays(event.target.value)}
                disabled={creating}
                required
                className="w-full rounded-xl border border-slate-300 px-3 py-3 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              />
            </div>

            <button
              type="submit"
              disabled={creating || loading || approvedPrescriptions.length === 0}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {creating ? (
                <Loader2 size={17} className="animate-spin" />
              ) : (
                <Plus size={17} />
              )}
              Submit plan
            </button>
          </form>
        </section>

        <section>
          <div className="mb-4 flex items-center gap-2">
            <CalendarClock className="text-emerald-700" size={21} />
            <h2 className="text-xl font-bold text-slate-900">
              My refill plans
            </h2>
          </div>

          {loading ? (
            <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-12 text-slate-500">
              <Loader2 className="mr-2 animate-spin" size={20} />
              Loading refill plans...
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
              <CalendarClock
                className="mx-auto mb-3 text-slate-400"
                size={32}
              />
              <p className="font-semibold text-slate-800">
                No refill plans yet
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Create a plan using one of your approved prescriptions.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {plans.map((plan) => (
                <article
                  key={plan.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-slate-900">
                        Refill Plan #{plan.id}
                      </h3>
                      <p className="mt-1 text-sm text-slate-500">
                        Prescription #{plan.prescription_id}
                      </p>
                    </div>
                    <StatusBadge status={plan.status} />
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">Interval</p>
                      <p className="mt-1 font-semibold text-slate-900">
                        Every {plan.interval_days} days
                      </p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3">
                      <p className="text-xs text-slate-500">Next refill</p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {formatDate(plan.next_refill_at)}
                      </p>
                    </div>
                  </div>

                  {plan.review_note && (
                    <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
                      <span className="font-semibold">Pharmacist note: </span>
                      {plan.review_note}
                    </p>
                  )}

                  <div className="mt-4 flex flex-wrap gap-2">
                    {plan.status === "active" && (
                      <>
                        <button
                          type="button"
                          onClick={() => void handleCreateRequest(plan.id)}
                          disabled={actionId === plan.id}
                          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {actionId === plan.id ? (
                            <Loader2 size={14} className="animate-spin" />
                          ) : (
                            <RefreshCw size={14} />
                          )}
                          Request refill
                        </button>
                        <button
                          type="button"
                          onClick={() => void handlePlanStatus(plan.id, "paused")}
                          disabled={actionId === plan.id}
                          className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                        >
                          <Pause size={14} />
                          Pause
                        </button>
                      </>
                    )}

                    {plan.status === "paused" && (
                      <button
                        type="button"
                        onClick={() => void handlePlanStatus(plan.id, "active")}
                        disabled={actionId === plan.id}
                        className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                      >
                        <Play size={14} />
                        Resume plan
                      </button>
                    )}

                    {(plan.status === "active" ||
                      plan.status === "paused" ||
                      plan.status === "pending_review") && (
                      <button
                        type="button"
                        onClick={() =>
                          void handlePlanStatus(plan.id, "cancelled")
                        }
                        disabled={actionId === plan.id}
                        className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                      >
                        <XCircle size={14} />
                        Cancel plan
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section>
          <div className="mb-4 flex items-center gap-2">
            <Clock className="text-emerald-700" size={21} />
            <h2 className="text-xl font-bold text-slate-900">
              Refill request history
            </h2>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
              Loading refill requests...
            </div>
          ) : requests.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
              <CheckCircle2
                className="mx-auto mb-3 text-slate-400"
                size={32}
              />
              <p className="font-semibold text-slate-800">
                No refill requests yet
              </p>
              <p className="mt-1 text-sm text-slate-500">
                Requests submitted from active plans will appear here.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200 text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3 font-semibold">Request</th>
                      <th className="px-5 py-3 font-semibold">Plan</th>
                      <th className="px-5 py-3 font-semibold">Submitted</th>
                      <th className="px-5 py-3 font-semibold">Status</th>
                      <th className="px-5 py-3 font-semibold">Order</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {requests.map((request) => (
                      <tr key={request.id}>
                        <td className="whitespace-nowrap px-5 py-4 font-medium text-slate-900">
                          #{request.id}
                        </td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-600">
                          #{request.plan_id}
                        </td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-600">
                          {formatDate(request.created_at)}
                        </td>
                        <td className="whitespace-nowrap px-5 py-4">
                          <StatusBadge status={request.status} />
                        </td>
                        <td className="whitespace-nowrap px-5 py-4 text-slate-600">
                          {request.order_id ? `#${request.order_id}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        <p className="text-xs leading-relaxed text-slate-500">
          Refill plans and requests require pharmacist review. Submitting a
          request does not guarantee approval or create an order until it has
          been approved.
        </p>
      </div>
    </main>
  );
}
