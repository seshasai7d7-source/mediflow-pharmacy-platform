
import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  refillApi,
  type RefillPlan,
  type RefillRequest,
} from "../lib/api";

type ReviewDecision = "approved" | "rejected";

function formatDate(value: string | null) {
  if (!value) return "Not scheduled";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not scheduled";

  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending_review: "bg-amber-100 text-amber-800",
    active: "bg-emerald-100 text-emerald-800",
    approved: "bg-emerald-100 text-emerald-800",
    rejected: "bg-red-100 text-red-800",
    paused: "bg-slate-100 text-slate-700",
    cancelled: "bg-slate-100 text-slate-600",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
        styles[status] ?? "bg-slate-100 text-slate-700"
      }`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function PharmacistRefillsPage() {
  const [plans, setPlans] = useState<RefillPlan[]>([]);
  const [requests, setRequests] = useState<RefillRequest[]>([]);
  const [planNotes, setPlanNotes] = useState<Record<number, string>>({});
  const [requestNotes, setRequestNotes] = useState<Record<number, string>>({});

  const [loading, setLoading] = useState(true);
  const [actionKey, setActionKey] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [planData, requestData] = await Promise.all([
        refillApi.getPlanQueue(),
        refillApi.getRequestQueue(),
      ]);

      setPlans(planData);
      setRequests(requestData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the refill review queue.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  async function handlePlanReview(
    planId: number,
    decision: ReviewDecision,
  ) {
    const key = `plan-${planId}`;
    setActionKey(key);
    setError("");
    setSuccess("");

    try {
      await refillApi.reviewPlan(planId, {
        decision,
        review_note: planNotes[planId]?.trim() || undefined,
      });

      setSuccess(
        `Refill plan #${planId} ${decision} successfully.`,
      );
      setPlanNotes((current) => {
        const updated = { ...current };
        delete updated[planId];
        return updated;
      });

      await loadQueue();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to review the refill plan.",
      );
    } finally {
      setActionKey(null);
    }
  }

  async function handleRequestReview(
    requestId: number,
    decision: ReviewDecision,
  ) {
    const key = `request-${requestId}`;
    setActionKey(key);
    setError("");
    setSuccess("");

    try {
      const result = await refillApi.reviewRequest(requestId, {
        decision,
        review_note: requestNotes[requestId]?.trim() || undefined,
      });

      if (decision === "approved" && result.order) {
        setSuccess(
          `Refill request #${requestId} approved. Order #${result.order.id} created.`,
        );
      } else {
        setSuccess(
          `Refill request #${requestId} ${decision} successfully.`,
        );
      }

      setRequestNotes((current) => {
        const updated = { ...current };
        delete updated[requestId];
        return updated;
      });

      await loadQueue();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to review the refill request.",
      );
    } finally {
      setActionKey(null);
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
              Refill Review
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Review customer refill plans and requests before authorization.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadQueue()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh queue
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

        <section className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  Pending refill plans
                </p>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {plans.length}
                </p>
              </div>
              <div className="rounded-xl bg-amber-100 p-3 text-amber-700">
                <Clock size={24} />
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">
                  Pending refill requests
                </p>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {requests.length}
                </p>
              </div>
              <div className="rounded-xl bg-emerald-100 p-3 text-emerald-700">
                <RefreshCw size={24} />
              </div>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-16 text-slate-500">
            <Loader2 className="mr-2 animate-spin" size={20} />
            Loading refill review queue...
          </div>
        ) : (
          <>
            <section>
              <div className="mb-4">
                <h2 className="text-xl font-bold text-slate-900">
                  Refill plan approvals
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Check the prescription and requested refill interval before
                  approving a plan.
                </p>
              </div>

              {plans.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
                  <CheckCircle2
                    className="mx-auto mb-3 text-emerald-500"
                    size={32}
                  />
                  <p className="font-semibold text-slate-800">
                    No pending refill plans
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    New customer refill plans will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
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
                            Customer #{plan.customer_id} · Prescription #
                            {plan.prescription_id}
                          </p>
                        </div>
                        <StatusBadge status={plan.status} />
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-3">
                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">
                            Refill interval
                          </p>
                          <p className="mt-1 font-semibold text-slate-900">
                            Every {plan.interval_days} days
                          </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">
                            Submitted
                          </p>
                          <p className="mt-1 font-semibold text-slate-900">
                            {formatDate(plan.created_at)}
                          </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">
                            Current next refill
                          </p>
                          <p className="mt-1 font-semibold text-slate-900">
                            {formatDate(plan.next_refill_at)}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4">
                        <label
                          htmlFor={`plan-note-${plan.id}`}
                          className="mb-2 block text-sm font-medium text-slate-700"
                        >
                          Review note (optional)
                        </label>
                        <textarea
                          id={`plan-note-${plan.id}`}
                          rows={2}
                          maxLength={500}
                          value={planNotes[plan.id] ?? ""}
                          onChange={(event) =>
                            setPlanNotes((current) => ({
                              ...current,
                              [plan.id]: event.target.value,
                            }))
                          }
                          placeholder="Add a note for the customer..."
                          disabled={actionKey === `plan-${plan.id}`}
                          className="w-full resize-y rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                        />
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            void handlePlanReview(plan.id, "approved")
                          }
                          disabled={actionKey === `plan-${plan.id}`}
                          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {actionKey === `plan-${plan.id}` ? (
                            <Loader2
                              size={16}
                              className="animate-spin"
                            />
                          ) : (
                            <CheckCircle2 size={16} />
                          )}
                          Approve plan
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            void handlePlanReview(plan.id, "rejected")
                          }
                          disabled={actionKey === `plan-${plan.id}`}
                          className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                        >
                          <XCircle size={16} />
                          Reject plan
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <section>
              <div className="mb-4">
                <h2 className="text-xl font-bold text-slate-900">
                  Refill request approvals
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Review each due refill request. Approving a request creates a
                  refill order.
                </p>
              </div>

              {requests.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center">
                  <CheckCircle2
                    className="mx-auto mb-3 text-emerald-500"
                    size={32}
                  />
                  <p className="font-semibold text-slate-800">
                    No pending refill requests
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    Customer refill requests will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {requests.map((request) => (
                    <article
                      key={request.id}
                      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h3 className="font-bold text-slate-900">
                            Refill Request #{request.id}
                          </h3>
                          <p className="mt-1 text-sm text-slate-500">
                            Refill Plan #{request.plan_id}
                          </p>
                        </div>
                        <StatusBadge status={request.status} />
                      </div>

                      <div className="mt-4 grid gap-3 sm:grid-cols-2">
                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">
                            Submitted
                          </p>
                          <p className="mt-1 font-semibold text-slate-900">
                            {formatDate(request.created_at)}
                          </p>
                        </div>

                        <div className="rounded-xl bg-slate-50 p-3">
                          <p className="text-xs text-slate-500">
                            Related order
                          </p>
                          <p className="mt-1 font-semibold text-slate-900">
                            {request.order_id
                              ? `Order #${request.order_id}`
                              : "Not created yet"}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4">
                        <label
                          htmlFor={`request-note-${request.id}`}
                          className="mb-2 block text-sm font-medium text-slate-700"
                        >
                          Review note (optional)
                        </label>
                        <textarea
                          id={`request-note-${request.id}`}
                          rows={2}
                          maxLength={500}
                          value={requestNotes[request.id] ?? ""}
                          onChange={(event) =>
                            setRequestNotes((current) => ({
                              ...current,
                              [request.id]: event.target.value,
                            }))
                          }
                          placeholder="Add a note for the customer..."
                          disabled={actionKey === `request-${request.id}`}
                          className="w-full resize-y rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                        />
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            void handleRequestReview(request.id, "approved")
                          }
                          disabled={actionKey === `request-${request.id}`}
                          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {actionKey === `request-${request.id}` ? (
                            <Loader2
                              size={16}
                              className="animate-spin"
                            />
                          ) : (
                            <CheckCircle2 size={16} />
                          )}
                          Approve and create order
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            void handleRequestReview(request.id, "rejected")
                          }
                          disabled={actionKey === `request-${request.id}`}
                          className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                        >
                          <XCircle size={16} />
                          Reject request
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        <p className="text-xs leading-relaxed text-slate-500">
          Review refill requests against the approved prescription and
          applicable pharmacy rules. Approval is a pharmacist action; the
          system does not independently authorize medication refills.
        </p>
      </div>
    </main>
  );
}
