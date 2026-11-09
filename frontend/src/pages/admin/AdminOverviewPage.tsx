
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertCircle,
  Boxes,
  ClipboardList,
  RefreshCw,
  ShieldCheck,
  Store,
  Users,
} from "lucide-react";

import {
  adminApi,
  type AdminPlatformOverview,
} from "../../lib/api";

function MetricCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: number;
  icon: typeof Users;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <div className="rounded-xl bg-emerald-50 p-2 text-emerald-700">
          <Icon size={20} />
        </div>
      </div>
      <p className="mt-4 text-3xl font-bold text-slate-900">
        {value.toLocaleString("en-IN")}
      </p>
    </div>
  );
}

function BreakdownCard({
  title,
  values,
}: {
  title: string;
  values: Record<string, number>;
}) {
  const entries = Object.entries(values).filter(
    ([key]) => key !== "total",
  );

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>

      <div className="mt-4 divide-y divide-slate-100">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between gap-4 py-3"
          >
            <span className="text-sm capitalize text-slate-600">
              {key.replace(/_/g, " ")}
            </span>
            <span className="text-sm font-semibold tabular-nums text-slate-900">
              {value.toLocaleString("en-IN")}
            </span>
          </div>
        ))}

        {entries.length === 0 && (
          <p className="py-3 text-sm text-slate-500">
            No breakdown data available.
          </p>
        )}
      </div>
    </section>
  );
}

export default function AdminOverviewPage() {
  const [overview, setOverview] =
    useState<AdminPlatformOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await adminApi.getOverview();
      setOverview(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load platform overview.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-5 py-10">
        <div className="flex items-center gap-3 text-slate-600">
          <RefreshCw className="animate-spin" size={20} />
          Loading platform overview...
        </div>
      </main>
    );
  }

  if (error || !overview) {
    return (
      <main className="mx-auto max-w-7xl px-5 py-10">
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6">
          <div className="flex items-center gap-3 text-rose-700">
            <AlertCircle size={22} />
            <h1 className="font-semibold">
              Unable to load platform overview
            </h1>
          </div>

          <p className="mt-2 text-sm text-rose-700">
            {error || "No overview data was returned."}
          </p>

          <button
            onClick={() => void loadOverview()}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-rose-700 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-800"
          >
            <RefreshCw size={16} />
            Try again
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Administration
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            Platform Overview
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Operational statistics from the MediFlow database.
          </p>
        </div>

        <button
          onClick={() => void loadOverview()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">
          Platform metrics
        </h2>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total users"
            value={overview.users.total ?? 0}
            icon={Users}
          />
          <MetricCard
            title="Total stores"
            value={overview.stores.total ?? 0}
            icon={Store}
          />
          <MetricCard
            title="Total orders"
            value={overview.orders.total ?? 0}
            icon={ClipboardList}
          />
          <MetricCard
            title="Total prescriptions"
            value={overview.prescriptions.total ?? 0}
            icon={ShieldCheck}
          />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">
          Operational breakdown
        </h2>

        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          <BreakdownCard title="Users" values={overview.users} />
          <BreakdownCard title="Stores" values={overview.stores} />
          <BreakdownCard title="Orders" values={overview.orders} />
          <BreakdownCard
            title="Prescriptions"
            values={overview.prescriptions}
          />
        </div>
      </section>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-emerald-50 p-3 text-emerald-700">
            <Boxes size={22} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              Inventory summary
            </h2>
            <p className="text-sm text-slate-500">
              Current inventory quantities across recorded inventory entries.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-sm text-slate-500">Inventory records</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {(overview.inventory.records ?? 0).toLocaleString("en-IN")}
            </p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-sm text-slate-500">Available quantity</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {(overview.inventory.available_quantity ?? 0).toLocaleString("en-IN")}
            </p>
          </div>

          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-sm text-slate-500">Reserved quantity</p>
            <p className="mt-2 text-2xl font-bold text-slate-900">
              {(overview.inventory.reserved_quantity ?? 0).toLocaleString("en-IN")}
            </p>
          </div>
        </div>
      </section>

      <div className="mt-6 flex items-start gap-2 text-xs text-slate-500">
        <Activity size={15} className="mt-0.5 shrink-0" />
        <p>
          Figures reflect database records. This prototype does not process
          payments, so revenue is intentionally excluded.
        </p>
      </div>
    </main>
  );
}
