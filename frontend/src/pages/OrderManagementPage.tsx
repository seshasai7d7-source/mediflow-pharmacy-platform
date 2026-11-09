
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ClipboardList,
  RefreshCw,
  Package,
} from "lucide-react";

import {
  ApiError,
  orderApi,
  type OrderResponse,
  type OrderStatus,
  type OrderStatusUpdate,
} from "../lib/api";

const allowedTransitions: Record<OrderStatus, OrderStatusUpdate[]> = {
  pending_review: [],
  confirmed: ["preparing", "cancelled"],
  preparing: ["ready", "cancelled"],
  ready: ["dispatched", "cancelled"],
  dispatched: ["delivered"],
  delivered: [],
  cancelled: [],
};

const statusStyles: Record<OrderStatus, string> = {
  pending_review: "bg-amber-100 text-amber-800",
  confirmed: "bg-blue-100 text-blue-800",
  preparing: "bg-indigo-100 text-indigo-800",
  ready: "bg-violet-100 text-violet-800",
  dispatched: "bg-cyan-100 text-cyan-800",
  delivered: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-rose-100 text-rose-800",
};

function formatDate(value: string): string {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
  }).format(value);
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ");
}

export default function OrderManagementPage() {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busyOrderId, setBusyOrderId] = useState<number | null>(null);

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await orderApi.getAllOrders();
      setOrders(data);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load pharmacy orders.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOrders();
  }, [loadOrders]);

  async function handleStatusUpdate(
    orderId: number,
    newStatus: OrderStatusUpdate,
  ) {
    const confirmed = window.confirm(
      `Change order status to "${formatStatus(newStatus)}"?`,
    );

    if (!confirmed) return;

    setBusyOrderId(orderId);
    setError("");
    setSuccess("");

    try {
      const updatedOrder = await orderApi.updateOrderStatus(
        orderId,
        newStatus,
      );

      setOrders((currentOrders) =>
        currentOrders.map((order) =>
          order.id === orderId ? updatedOrder : order,
        ),
      );

      setSuccess(
        `Order ${updatedOrder.order_number} updated to ${formatStatus(updatedOrder.status)}.`,
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to update the order status.",
      );
    } finally {
      setBusyOrderId(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link
            to="/dashboard"
            className="flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-emerald-700"
          >
            <ArrowLeft size={18} />
            Dashboard
          </Link>

          <button
            type="button"
            onClick={() => void loadOrders()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="rounded-3xl bg-emerald-800 p-7 text-white sm:p-9">
          <div className="flex items-center gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white/10">
              <ClipboardList size={25} />
            </div>

            <div>
              <p className="text-sm text-emerald-100">
                Pharmacist workspace
              </p>
              <h1 className="text-2xl font-semibold">
                Order Management
              </h1>
            </div>
          </div>

          <p className="mt-4 max-w-xl text-sm leading-6 text-emerald-100">
            Review pharmacy orders, inspect medicine quantities,
            and manage order fulfilment status.
          </p>

          <div className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-3">
            <Package size={18} />
            <span className="text-sm font-medium">
              {orders.length} total order{orders.length === 1 ? "" : "s"}
            </span>
          </div>
        </div>

        {error && (
          <div
            role="alert"
            className="mt-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700"
          >
            {error}
          </div>
        )}

        {success && (
          <div
            role="status"
            className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700"
          >
            {success}
          </div>
        )}

        <div className="mt-8">
          {loading ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-500">
              Loading pharmacy orders...
            </div>
          ) : orders.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center">
              <Package className="mx-auto text-slate-400" size={34} />
              <h2 className="mt-4 font-semibold text-slate-800">
                No orders found
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                Customer orders will appear here when they are created.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              {orders.map((order) => {
                const nextStatuses =
                  allowedTransitions[order.status] ?? [];

                return (
                  <article
                    key={order.id}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
                          Order number
                        </p>
                        <h2 className="mt-1 text-lg font-semibold text-slate-900">
                          {order.order_number}
                        </h2>
                        <p className="mt-1 text-xs text-slate-500">
                          Order ID: {order.id}
                        </p>
                      </div>

                      <span
                        className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize ${
                          statusStyles[order.status]
                        }`}
                      >
                        {formatStatus(order.status)}
                      </span>
                    </div>

                    <div className="mt-5 grid gap-4 rounded-xl bg-slate-50 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
                      <div>
                        <p className="text-xs text-slate-500">
                          Customer ID
                        </p>
                        <p className="mt-1 font-semibold text-slate-800">
                          {order.customer_id}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">
                          Store ID
                        </p>
                        <p className="mt-1 font-semibold text-slate-800">
                          {order.store_id ?? "Not assigned"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">
                          Prescription ID
                        </p>
                        <p className="mt-1 font-semibold text-slate-800">
                          {order.prescription_id ?? "N/A"}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs text-slate-500">
                          Created
                        </p>
                        <p className="mt-1 font-semibold text-slate-800">
                          {formatDate(order.created_at)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-5">
                      <h3 className="text-sm font-semibold text-slate-800">
                        Order items
                      </h3>

                      <div className="mt-3 overflow-x-auto">
                        <table className="w-full min-w-[400px] text-left text-sm">
                          <thead>
                            <tr className="border-b border-slate-200 text-xs text-slate-500">
                              <th className="py-2 pr-4">Medicine ID</th>
                              <th className="py-2 pr-4">Quantity</th>
                              <th className="py-2 text-right">Unit price</th>
                            </tr>
                          </thead>

                          <tbody>
                            {order.items.map((item) => (
                              <tr
                                key={item.id}
                                className="border-b border-slate-100 last:border-0"
                              >
                                <td className="py-3 pr-4 font-medium text-slate-800">
                                  {item.medicine_id}
                                </td>
                                <td className="py-3 pr-4 text-slate-600">
                                  {item.quantity}
                                </td>
                                <td className="py-3 text-right text-slate-600">
                                  {formatCurrency(item.unit_price)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4">
                      <div>
                        <p className="text-xs text-slate-500">
                          Order total
                        </p>
                        <p className="mt-1 text-lg font-semibold text-slate-900">
                          {formatCurrency(order.total_amount)}
                        </p>
                        {order.total_amount === 0 && (
                          <p className="mt-1 text-xs text-amber-700">
                            Demo pricing placeholder; payment is not enabled.
                          </p>
                        )}
                      </div>

                      {nextStatuses.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {nextStatuses.map((nextStatus) => (
                            <button
                              key={nextStatus}
                              type="button"
                              disabled={busyOrderId === order.id}
                              onClick={() =>
                                void handleStatusUpdate(
                                  order.id,
                                  nextStatus,
                                )
                              }
                              className={`rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                                nextStatus === "cancelled"
                                  ? "border border-rose-200 text-rose-700 hover:bg-rose-50"
                                  : "bg-emerald-700 text-white hover:bg-emerald-800"
                              }`}
                            >
                              {busyOrderId === order.id
                                ? "Updating..."
                                : `Mark ${formatStatus(nextStatus)}`}
                            </button>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs font-medium text-slate-500">
                          No further status transitions available.
                        </p>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
