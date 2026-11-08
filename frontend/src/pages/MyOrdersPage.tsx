
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Package,
  RefreshCw,
  ShoppingBag,
  Clock,
  CheckCircle,
  Truck,
  XCircle,
  AlertCircle,
} from "lucide-react";

import {
  orderApi,
  ApiError,
  type OrderResponse,
} from "../lib/api";

const statusConfig: Record<
  OrderResponse["status"],
  { label: string; className: string; icon: typeof Clock }
> = {
  pending_review: {
    label: "Pending review",
    className: "bg-amber-50 text-amber-700",
    icon: Clock,
  },
  confirmed: {
    label: "Confirmed",
    className: "bg-blue-50 text-blue-700",
    icon: CheckCircle,
  },
  preparing: {
    label: "Preparing",
    className: "bg-indigo-50 text-indigo-700",
    icon: Package,
  },
  ready: {
    label: "Ready for dispatch",
    className: "bg-emerald-50 text-emerald-700",
    icon: CheckCircle,
  },
  dispatched: {
    label: "Dispatched",
    className: "bg-purple-50 text-purple-700",
    icon: Truck,
  },
  delivered: {
    label: "Delivered",
    className: "bg-green-50 text-green-700",
    icon: CheckCircle,
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-rose-50 text-rose-700",
    icon: XCircle,
  },
};

export default function MyOrdersPage() {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadOrders() {
    setLoading(true);
    setError("");

    try {
      const data = await orderApi.getMyOrders();
      setOrders(data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load your orders.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOrders();
  }, []);

  function formatAmount(amount: number) {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(Number(amount));
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
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-100 text-emerald-700">
              <ShoppingBag size={25} />
            </div>

            <div>
              <h1 className="text-2xl font-semibold text-slate-900">
                My Orders
              </h1>
              <p className="text-sm text-slate-500">
                View your medicine orders and their status.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={loadOrders}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={15} />
            Refresh orders
          </button>
        </div>

        {error && (
          <div className="mt-6 flex items-start gap-2 rounded-xl bg-rose-50 p-4 text-sm text-rose-700">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
            Loading your orders...
          </div>
        ) : orders.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <Package
              className="mx-auto text-slate-400"
              size={40}
            />
            <h2 className="mt-4 font-semibold text-slate-800">
              No orders yet
            </h2>
            <p className="mt-2 text-sm text-slate-500">
              Orders created from your approved prescriptions will appear here.
            </p>
            <Link
              to="/prescriptions"
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800"
            >
              <ShoppingBag size={17} />
              View prescriptions
            </Link>
          </div>
        ) : (
          <div className="mt-8 space-y-5">
            {orders.map((order) => {
              const config = statusConfig[order.status];
              const StatusIcon = config.icon;

              return (
                <article
                  key={order.id}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                >
                  <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                    <div>
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                        Order number
                      </p>
                      <h2 className="mt-1 text-lg font-semibold text-slate-900">
                        {order.order_number}
                      </h2>
                      <p className="mt-1 text-xs text-slate-500">
                        Placed on{" "}
                        {new Date(order.created_at).toLocaleString("en-IN")}
                      </p>
                    </div>

                    <span
                      className={`inline-flex w-fit items-center gap-2 rounded-full px-3 py-2 text-xs font-semibold ${config.className}`}
                    >
                      <StatusIcon size={14} />
                      {config.label}
                    </span>
                  </div>

                  <div className="mt-5 grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-slate-500">Order ID</p>
                      <p className="mt-1 font-medium text-slate-800">
                        #{order.id}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-slate-500">Assigned store</p>
                      <p className="mt-1 font-medium text-slate-800">
                        {order.store_id !== null
                          ? `Store #${order.store_id}`
                          : "Not assigned"}
                      </p>
                    </div>

                    <div>
                      <p className="text-xs text-slate-500">Order total</p>
                      <p className="mt-1 font-semibold text-slate-900">
                        {formatAmount(order.total_amount)}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 border-t border-slate-100 pt-5">
                    <h3 className="text-sm font-semibold text-slate-800">
                      Ordered medicines
                    </h3>

                    <div className="mt-3 space-y-3">
                      {order.items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between gap-4 text-sm"
                        >
                          <div>
                            <p className="font-medium text-slate-700">
                              Medicine #{item.medicine_id}
                            </p>
                            <p className="text-xs text-slate-500">
                              Quantity: {item.quantity}
                            </p>
                          </div>

                          <p className="font-medium text-slate-700">
                            {formatAmount(
                              item.unit_price * item.quantity,
                            )}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
