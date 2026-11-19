import { useEffect, useState } from "react";
import { HeartPulse, LogOut, PackageSearch } from "lucide-react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import {
  ApiError,
  inventoryApi,
  storeApi,
  type AdminStore,
  type MedicineCatalogueItem,
  type MedicineCatalogueResponse,
} from "../lib/api";

const PAGE_SIZE = 20;

export default function MedicineCataloguePage() {
  const { user, logout } = useAuth();
  const [search, setSearch] = useState("");
  const [storeId, setStoreId] = useState<number | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const [stores, setStores] = useState<AdminStore[]>([]);
  const [catalogue, setCatalogue] = useState<MedicineCatalogueResponse>({
    items: [],
    total: 0,
    skip: 0,
    limit: 20,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    storeApi
      .getStores()
      .then((result) => {
        if (active) setStores(result);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof ApiError ? reason.message : "Unable to load stores.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    inventoryApi
      .getCatalogue({
        search: search.trim() || undefined,
        store_id: storeId,
        skip: (currentPage - 1) * PAGE_SIZE,
        limit: PAGE_SIZE,
      })
      .then((result) => {
        if (active) setCatalogue(result);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof ApiError ? reason.message : "Unable to load medicines.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [search, storeId, currentPage]);

  if (!user) return null;

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link to="/dashboard" className="flex items-center gap-2 text-xl font-bold text-emerald-950">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-700 text-white">
              <HeartPulse size={22} />
            </span>
            MediFlow
          </Link>
          <button type="button" onClick={logout} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-emerald-700">Customer catalogue</p>
            <h1 className="mt-1 text-3xl font-semibold text-slate-900">Browse medicines</h1>
          </div>
          <Link to="/dashboard" className="text-sm font-semibold text-emerald-700">Back to dashboard</Link>
        </div>

        <div className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-[1fr_260px]">
          <label className="text-sm font-medium text-slate-700">
            Search
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setCurrentPage(1);
              }}
              placeholder="Medicine, generic name, or brand"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 font-normal outline-none focus:border-emerald-700"
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Pharmacy store
            <select
              value={storeId ?? ""}
              onChange={(event) => {
                setStoreId(event.target.value ? Number(event.target.value) : undefined);
                setCurrentPage(1);
              }}
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 font-normal outline-none focus:border-emerald-700"
            >
              <option value="">All active stores</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>{store.name} - {store.city}</option>
              ))}
            </select>
          </label>
        </div>

        {loading ? (
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-500">Loading medicines...</div>
        ) : error ? (
          <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">{error}</div>
        ) : catalogue.items.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-10 text-center">
            <PackageSearch className="mx-auto text-slate-400" size={34} />
            <h2 className="mt-3 font-semibold text-slate-900">No medicines found</h2>
            <p className="mt-2 text-sm text-slate-500">Try another search or pharmacy store.</p>
          </div>
        ) : (
          <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {catalogue.items.map((medicine: MedicineCatalogueItem) => (
              <article key={medicine.id} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold text-slate-900">{medicine.name}</h2>
                    {medicine.brand_name && <p className="mt-1 text-sm text-slate-500">Brand: {medicine.brand_name}</p>}
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${medicine.is_available ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>
                    {medicine.is_available ? "Available" : "Unavailable"}
                  </span>
                </div>
                <dl className="mt-4 space-y-2 text-sm text-slate-600">
                  {medicine.generic_name && <div><dt className="text-xs text-slate-400">Generic</dt><dd>{medicine.generic_name}</dd></div>}
                  {medicine.strength && <div><dt className="text-xs text-slate-400">Strength</dt><dd>{medicine.strength}</dd></div>}
                  {medicine.dosage_form && <div><dt className="text-xs text-slate-400">Dosage form</dt><dd>{medicine.dosage_form}</dd></div>}
                  <div><dt className="text-xs text-slate-400">Schedule</dt><dd>{medicine.schedule_category}</dd></div>
                </dl>
                <p className={`mt-4 text-sm font-medium ${medicine.requires_prescription ? "text-amber-700" : "text-emerald-700"}`}>
                  {medicine.requires_prescription ? "Prescription required" : "No prescription indicated"}
                </p>
                {medicine.stores.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    {medicine.stores.map((store) => `${store.store_name} (${store.available_quantity} available)`).join("; ")}
                  </p>
                )}
                {medicine.requires_prescription && (
                  <Link to="/prescriptions" className="mt-4 inline-block text-sm font-semibold text-emerald-700">Upload prescription</Link>
                )}
              </article>
            ))}
          </div>
        )}
        {!loading && !error && catalogue.total > 0 && (
          <nav
            aria-label="Medicine catalogue pagination"
            className="mt-6 flex flex-wrap items-center justify-between gap-3"
          >
            <p className="text-sm text-slate-600" aria-live="polite">
              Showing {catalogue.skip + 1}-
              {Math.min(catalogue.skip + catalogue.items.length, catalogue.total)} of{" "}
              {catalogue.total} medicines
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => page - 1)}
                disabled={catalogue.skip === 0}
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-2 text-sm text-slate-600">
                Page {currentPage}
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => page + 1)}
                disabled={catalogue.skip + catalogue.limit >= catalogue.total}
                className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </nav>
        )}
      </section>
    </main>
  );
}
