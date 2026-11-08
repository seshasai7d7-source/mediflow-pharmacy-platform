
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  FileText,
  LoaderCircle,
  XCircle,
} from "lucide-react";

import {
  ApiError,
  pharmacistApi,
  type PharmacistMedicine,
  type PharmacistPrescriptionDetail,
} from "../lib/api";

interface ReviewMedicine {
  medicine_id: number;
  quantity: number;
  dosage: string;
  generic_substitution: boolean;
  customer_consent: boolean;
}

export default function PharmacistReviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const prescriptionId = Number(id);

  const [prescription, setPrescription] =
    useState<PharmacistPrescriptionDetail | null>(null);
  const [medicines, setMedicines] = useState<PharmacistMedicine[]>([]);
  const [selected, setSelected] = useState<ReviewMedicine[]>([]);
  const [rejectionReason, setRejectionReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      if (!Number.isInteger(prescriptionId) || prescriptionId <= 0) {
        throw new Error("Invalid prescription ID.");
      }

      const [detail, catalogue] = await Promise.all([
        pharmacistApi.getPrescription(prescriptionId),
        pharmacistApi.getMedicines(),
      ]);

      setPrescription(detail);
      setMedicines(catalogue);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Unable to load prescription details.",
      );
    } finally {
      setLoading(false);
    }
  }, [prescriptionId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const addMedicine = () => {
    setSelected((current) => [
      ...current,
      {
        medicine_id: 0,
        quantity: 1,
        dosage: "",
        generic_substitution: false,
        customer_consent: false,
      },
    ]);
  };

  const updateMedicine = (
    index: number,
    changes: Partial<ReviewMedicine>,
  ) => {
    setSelected((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...changes } : item,
      ),
    );
  };

  const removeMedicine = (index: number) => {
    setSelected((current) =>
      current.filter((_, itemIndex) => itemIndex !== index),
    );
  };

  const handleApprove = async () => {
    setError("");
    setSuccess("");

    if (!prescription) return;

    if (selected.length === 0) {
      setError("Add at least one verified medicine before approval.");
      return;
    }

    if (
      selected.some(
        (item) =>
          item.medicine_id <= 0 ||
          item.quantity <= 0 ||
          !Number.isInteger(item.quantity),
      )
    ) {
      setError("Select a medicine and enter a valid positive quantity for every item.");
      return;
    }

    if (
      selected.some(
        (item) =>
          item.generic_substitution && !item.customer_consent,
      )
    ) {
      setError("Customer consent is required for every generic substitution.");
      return;
    }

    const prohibited = selected.some((item) => {
      const medicine = medicines.find(
        (entry) => entry.id === item.medicine_id,
      );
      return (
        !medicine ||
        medicine.schedule_category === "X" ||
        medicine.schedule_category === "NARCOTIC" ||
        medicine.schedule_category === "UNKNOWN"
      );
    });

    if (prohibited) {
      setError(
        "One or more selected medicines are unavailable or have a prohibited/unknown schedule category.",
      );
      return;
    }

    setSubmitting(true);

    try {
      await pharmacistApi.reviewPrescription(prescription.id, {
        decision: "approved",
        medicines: selected.map((item) => ({
          medicine_id: item.medicine_id,
          quantity: item.quantity,
          dosage: item.dosage.trim() || undefined,
          generic_substitution: item.generic_substitution,
          customer_consent: item.customer_consent,
        })),
      });

      setSuccess("Prescription approved successfully.");
      window.setTimeout(() => {
        navigate("/pharmacist/prescriptions");
      }, 1000);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to approve this prescription.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    setError("");
    setSuccess("");

    if (!prescription) return;

    const reason = rejectionReason.trim();

    if (!reason) {
      setError("Enter a rejection reason.");
      return;
    }

    if (reason.length > 500) {
      setError("Rejection reason must be 500 characters or fewer.");
      return;
    }

    setSubmitting(true);

    try {
      await pharmacistApi.reviewPrescription(prescription.id, {
        decision: "rejected",
        rejection_reason: reason,
      });

      setSuccess("Prescription rejected successfully.");
      window.setTimeout(() => {
        navigate("/pharmacist/prescriptions");
      }, 1000);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to reject this prescription.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50">
        <p className="flex items-center gap-2 text-slate-600">
          <LoaderCircle className="animate-spin" size={18} />
          Loading prescription...
        </p>
      </main>
    );
  }

  if (!prescription) {
    return (
      <main className="min-h-screen bg-slate-50 p-8">
        <div className="mx-auto max-w-3xl rounded-2xl border border-rose-200 bg-white p-6">
          <p className="font-semibold text-rose-700">
            Could not load prescription
          </p>
          <p className="mt-2 text-sm text-slate-600">{error}</p>
          <Link
            to="/pharmacist/prescriptions"
            className="mt-4 inline-block text-sm font-semibold text-emerald-700"
          >
            Back to queue
          </Link>
        </div>
      </main>
    );
  }

  const alreadyReviewed = prescription.status !== "uploaded";

  return (
    <main className="min-h-screen bg-slate-50 px-5 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <Link
          to="/pharmacist/prescriptions"
          className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 hover:underline"
        >
          <ArrowLeft size={16} />
          Back to prescription queue
        </Link>

        <header className="mb-8 mt-4">
          <h1 className="text-3xl font-bold text-slate-900">
            Review prescription #{prescription.id}
          </h1>
          <p className="mt-2 text-slate-600">
            Verify the prescription and medicine details before making a decision.
          </p>
        </header>

        {error && (
          <div className="mb-5 flex gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            <AlertCircle size={18} className="shrink-0" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-5 flex gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            <CheckCircle size={18} />
            {success}
          </div>
        )}

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-semibold text-slate-900">
            Customer and upload details
          </h2>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-slate-500">Customer</p>
              <p className="mt-1 font-medium text-slate-800">
                {prescription.customer_name}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Email</p>
              <p className="mt-1 font-medium text-slate-800">
                {prescription.customer_email}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Original filename</p>
              <p className="mt-1 flex items-center gap-2 font-medium text-slate-800">
                <FileText size={16} />
                {prescription.original_filename}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Uploaded</p>
              <p className="mt-1 font-medium text-slate-800">
                {new Date(prescription.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          <p className="mt-4 text-sm text-slate-500">
            File type: {prescription.mime_type}
          </p>
        </section>

        <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <h2 className="font-semibold text-amber-900">
            AI extraction draft — not verified
          </h2>
          <p className="mt-1 text-sm text-amber-800">
            Treat extracted information as a draft only. Independently verify all details against the original prescription.
          </p>

          <pre className="mt-4 max-h-72 overflow-auto rounded-xl bg-white p-4 text-xs text-slate-700">
            {JSON.stringify(
              prescription.ai_extraction_json ?? {
                message: "No AI extraction data is available.",
              },
              null,
              2,
            )}
          </pre>
        </section>

        {prescription.items.length > 0 && (
          <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-slate-900">
              Previously recorded prescription items
            </h2>
            <div className="mt-4 space-y-3">
              {prescription.items.map((item) => (
                <div
                  key={item.id}
                  className="rounded-xl bg-slate-50 p-4 text-sm"
                >
                  <p className="font-medium text-slate-800">
                    {item.extracted_name}
                  </p>
                  <p className="mt-1 text-slate-600">
                    Dosage: {item.dosage ?? "Not specified"} · Quantity:{" "}
                    {item.quantity ?? "Not specified"}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {alreadyReviewed ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="font-semibold text-slate-900">
              Review completed
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Current status: {prescription.status}
            </p>
            {prescription.rejection_reason && (
              <p className="mt-2 text-sm text-rose-700">
                Reason: {prescription.rejection_reason}
              </p>
            )}
          </section>
        ) : (
          <>
            <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-slate-900">
                    Verified medicines
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Select the medicines that you have independently verified.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={addMedicine}
                  className="rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800"
                >
                  Add medicine
                </button>
              </div>

              {selected.length === 0 && (
                <p className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                  No medicines added yet.
                </p>
              )}

              <div className="mt-5 space-y-5">
                {selected.map((item, index) => (
                  <div
                    key={index}
                    className="rounded-xl border border-slate-200 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold text-slate-800">
                        Medicine {index + 1}
                      </h3>
                      <button
                        type="button"
                        onClick={() => removeMedicine(index)}
                        className="text-sm font-medium text-rose-600 hover:underline"
                      >
                        Remove
                      </button>
                    </div>

                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      <label className="text-sm font-medium text-slate-700">
                        Active medicine
                        <select
                          value={item.medicine_id || ""}
                          onChange={(event) =>
                            updateMedicine(index, {
                              medicine_id: Number(event.target.value),
                            })
                          }
                          className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
                        >
                          <option value="">Select medicine</option>
                          {medicines.map((medicine) => (
                            <option
                              key={medicine.id}
                              value={medicine.id}
                              disabled={
                                medicine.schedule_category === "X" ||
                                medicine.schedule_category === "NARCOTIC" ||
                                medicine.schedule_category === "UNKNOWN"
                              }
                            >
                              {medicine.name}
                              {medicine.strength
                                ? ` — ${medicine.strength}`
                                : ""}
                              {` (${medicine.schedule_category})`}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label className="text-sm font-medium text-slate-700">
                        Quantity
                        <input
                          type="number"
                          min="1"
                          step="1"
                          value={item.quantity}
                          onChange={(event) =>
                            updateMedicine(index, {
                              quantity: Number(event.target.value),
                            })
                          }
                          className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5"
                        />
                      </label>

                      <label className="text-sm font-medium text-slate-700 sm:col-span-2">
                        Dosage instructions
                        <input
                          type="text"
                          maxLength={150}
                          value={item.dosage}
                          onChange={(event) =>
                            updateMedicine(index, {
                              dosage: event.target.value,
                            })
                          }
                          placeholder="Enter verified dosage instructions"
                          className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5"
                        />
                      </label>
                    </div>

                    <div className="mt-4 space-y-3">
                      <label className="flex items-start gap-3 text-sm text-slate-700">
                        <input
                          type="checkbox"
                          checked={item.generic_substitution}
                          onChange={(event) =>
                            updateMedicine(index, {
                              generic_substitution: event.target.checked,
                              customer_consent: event.target.checked
                                ? item.customer_consent
                                : false,
                            })
                          }
                          className="mt-1"
                        />
                        Generic substitution proposed and verified
                      </label>

                      {item.generic_substitution && (
                        <label className="flex items-start gap-3 text-sm text-slate-700">
                          <input
                            type="checkbox"
                            checked={item.customer_consent}
                            onChange={(event) =>
                              updateMedicine(index, {
                                customer_consent: event.target.checked,
                              })
                            }
                            className="mt-1"
                          />
                          Customer consent obtained for this substitution
                        </label>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-5 text-xs leading-5 text-slate-500">
                Medicines classified as Schedule X, narcotic, or UNKNOWN cannot be approved through this workflow. Verify applicable prescription requirements before approval.
              </p>
            </section>

            <section className="mb-6 rounded-2xl border border-rose-200 bg-white p-6">
              <h2 className="font-semibold text-slate-900">
                Reject prescription
              </h2>
              <label className="mt-4 block text-sm font-medium text-slate-700">
                Rejection reason
                <textarea
                  value={rejectionReason}
                  onChange={(event) =>
                    setRejectionReason(event.target.value)
                  }
                  maxLength={500}
                  rows={3}
                  placeholder="Explain why this prescription cannot be accepted."
                  className="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5"
                />
              </label>
              <p className="mt-1 text-right text-xs text-slate-400">
                {rejectionReason.length}/500
              </p>
            </section>

            <div className="flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={() => void handleReject()}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-300 bg-white px-5 py-3 font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
              >
                <XCircle size={18} />
                Reject prescription
              </button>

              <button
                type="button"
                onClick={() => void handleApprove()}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800 disabled:opacity-50"
              >
                {submitting ? (
                  <LoaderCircle className="animate-spin" size={18} />
                ) : (
                  <CheckCircle size={18} />
                )}
                Approve prescription
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
