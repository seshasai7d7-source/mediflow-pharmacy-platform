
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  Upload,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  ShoppingCart,
} from "lucide-react";

import {
  prescriptionApi,
  orderApi,
  ApiError,
  type Prescription,
  type PrescriptionStatus,
} from "../lib/api";

const statusConfig: Record<
  PrescriptionStatus,
  { label: string; className: string; icon: typeof Clock }
> = {
  uploaded: {
    label: "Uploaded",
    className: "bg-blue-50 text-blue-700",
    icon: Clock,
  },
  processing: {
    label: "Processing",
    className: "bg-amber-50 text-amber-700",
    icon: RefreshCw,
  },
  reupload_required: {
    label: "Re-upload required",
    className: "bg-orange-50 text-orange-700",
    icon: AlertCircle,
  },
  approved: {
    label: "Approved",
    className: "bg-emerald-50 text-emerald-700",
    icon: CheckCircle,
  },
  rejected: {
    label: "Rejected",
    className: "bg-rose-50 text-rose-700",
    icon: XCircle,
  },
};

export default function MyPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [orderingPrescriptionId, setOrderingPrescriptionId] =
    useState<number | null>(null);

  async function loadPrescriptions() {
    setLoading(true);
    setError("");

    try {
      const data = await prescriptionApi.getMyPrescriptions();
      setPrescriptions(data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load your prescriptions.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPrescriptions();
  }, []);

  async function handleUpload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Please select a prescription file.");
      return;
    }

    const allowedTypes = [
      "application/pdf",
      "image/jpeg",
      "image/png",
    ];

    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Only PDF, JPG, and PNG files are allowed.");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File size must not exceed 10 MB.");
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");

    try {
      await prescriptionApi.upload(selectedFile);
      setSelectedFile(null);
      setSuccess(
        "Prescription uploaded successfully. It will be reviewed by a pharmacist.",
      );

      const fileInput = document.getElementById(
        "prescription-file",
      ) as HTMLInputElement | null;

      if (fileInput) fileInput.value = "";

      await loadPrescriptions();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to upload your prescription.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleCreateOrder(prescriptionId: number) {
    setError("");
    setSuccess("");
    setOrderingPrescriptionId(prescriptionId);

    let usedLocation = false;

    const payload: {
      prescription_id: number;
      customer_latitude?: number;
      customer_longitude?: number;
    } = {
      prescription_id: prescriptionId,
    };

    try {
      if ("geolocation" in navigator) {
        try {
          const position = await new Promise<GeolocationPosition>(
            (resolve, reject) => {
              navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: false,
                timeout: 10000,
                maximumAge: 60000,
              });
            },
          );

          payload.customer_latitude = position.coords.latitude;
          payload.customer_longitude = position.coords.longitude;
          usedLocation = true;
        } catch {
          // Location unavailable; continue with default store selection.
        }
      }

      const order = await orderApi.createOrder(payload);

      setSuccess(
        `Order ${order.order_number} created successfully. ${
          usedLocation
            ? "Nearest eligible store selected."
            : "Default store selection used because location was unavailable."
        } Store ID: ${order.store_id ?? "Not assigned"}.`,
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to place your order.",
      );
    } finally {
      setOrderingPrescriptionId(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center px-5 py-4 sm:px-8">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-emerald-700"
          >
            <ArrowLeft size={18} />
            Back to dashboard
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-5 py-10 sm:px-8">
        <div>
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-100 text-emerald-700">
              <FileText size={25} />
            </div>

            <div>
              <h1 className="text-2xl font-semibold text-slate-900">
                My Prescriptions
              </h1>
              <p className="text-sm text-slate-500">
                Upload and track your prescription reviews.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            Upload a prescription
          </h2>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Select a clear prescription document. Accepted formats are PDF,
            JPG, and PNG, up to 10 MB.
          </p>

          <form onSubmit={handleUpload} className="mt-5 space-y-4">
            <input
              id="prescription-file"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
              onChange={(event) =>
                setSelectedFile(event.target.files?.[0] ?? null)
              }
              className="block w-full rounded-xl border border-slate-200 p-3 text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-4 file:py-2 file:font-medium file:text-emerald-700 hover:file:bg-emerald-100"
            />

            {selectedFile && (
              <p className="text-sm text-slate-600">
                Selected: {selectedFile.name}
              </p>
            )}

            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Upload size={17} />
              {uploading ? "Uploading..." : "Upload prescription"}
            </button>
          </form>

          {error && (
            <div className="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">
              {success}
            </div>
          )}
        </div>

        <div className="mt-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">
                Prescription history
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Track the review status of your uploaded documents.
              </p>
            </div>

            <button
              type="button"
              onClick={loadPrescriptions}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
            >
              <RefreshCw size={15} />
              Refresh
            </button>
          </div>

          {loading ? (
            <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
              Loading your prescriptions...
            </div>
          ) : prescriptions.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
              <FileText className="mx-auto text-slate-400" size={35} />
              <h3 className="mt-3 font-semibold text-slate-800">
                No prescriptions yet
              </h3>
              <p className="mt-2 text-sm text-slate-500">
                Your uploaded prescriptions will appear here.
              </p>
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              {prescriptions.map((prescription) => {
                const config = statusConfig[prescription.status];
                const StatusIcon = config.icon;
                const isOrdering =
                  orderingPrescriptionId === prescription.id;

                return (
                  <article
                    key={prescription.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                      <div className="flex items-start gap-3">
                        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                          <FileText size={21} />
                        </div>

                        <div className="min-w-0">
                          <h3 className="break-all font-semibold text-slate-800">
                            {prescription.original_filename}
                          </h3>

                          <p className="mt-1 text-xs text-slate-500">
                            Uploaded on{" "}
                            {new Date(
                              prescription.created_at,
                            ).toLocaleString()}
                          </p>

                          <p className="mt-1 text-xs text-slate-400">
                            Prescription ID: #{prescription.id}
                          </p>
                        </div>
                      </div>

                      <span
                        className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold ${config.className}`}
                      >
                        <StatusIcon size={14} />
                        {config.label}
                      </span>
                    </div>

                    {prescription.status === "approved" && (
                      <div className="mt-4 border-t border-slate-100 pt-4">
                        <p className="mb-3 text-sm text-slate-600">
                          Your prescription has been approved by a pharmacist.
                          You can now place an order.
                        </p>

                        <button
                          type="button"
                          onClick={() =>
                            handleCreateOrder(prescription.id)
                          }
                          disabled={orderingPrescriptionId !== null}
                          className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <ShoppingCart size={17} />
                          {isOrdering ? "Placing order..." : "Place order"}
                        </button>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>

        <div className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h3 className="font-semibold text-amber-900">
            Important safety information
          </h3>
          <p className="mt-2 text-sm leading-6 text-amber-800">
            Prescription extraction is only a preliminary aid. A pharmacist
            must review and approve every medicine before an order can be
            placed. Do not use this platform for medical advice.
          </p>
        </div>
      </section>
    </main>
  );
}
