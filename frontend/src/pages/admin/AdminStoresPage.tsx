import { useCallback, useEffect, useState } from "react";
import { Search, Store, MapPin, Pencil, ChevronLeft, ChevronRight, X, RefreshCw } from "lucide-react";
import { adminApi, type AdminStore, type AdminStoreUpdatePayload } from "../../lib/api";

const PAGE_SIZE = 10;

type StatusFilter = "all" | "active" | "inactive";

interface StoreForm {
  name: string;
  address: string;
  city: string;
  pincode: string;
  latitude: string;
  longitude: string;
  is_active: boolean;
}

const emptyForm: StoreForm = {
  name: "",
  address: "",
  city: "",
  pincode: "",
  latitude: "",
  longitude: "",
  is_active: true,
};

function toForm(store: AdminStore): StoreForm {
  return {
    name: store.name,
    address: store.address,
    city: store.city,
    pincode: store.pincode,
    latitude: store.latitude === null ? "" : String(store.latitude),
    longitude: store.longitude === null ? "" : String(store.longitude),
    is_active: store.is_active,
  };
}

export default function AdminStoresPage() {
  const [stores, setStores] = useState<AdminStore[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(0);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [selectedStore, setSelectedStore] = useState<AdminStore | null>(null);
  const [form, setForm] = useState<StoreForm>(emptyForm);

  const loadStores = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const response = await adminApi.getStores({
        search: search.trim() || undefined,
        is_active:
          statusFilter === "all" ? undefined : statusFilter === "active",
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });

      setStores(response.stores);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load stores.");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, page]);

  useEffect(() => {
    void loadStores();
  }, [loadStores]);

  function updateForm<K extends keyof StoreForm>(key: K, value: StoreForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function openStore(storeId: number) {
    setError("");
    setNotice("");

    try {
      const store = await adminApi.getStore(storeId);
      setSelectedStore(store);
      setForm(toForm(store));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load store details.");
    }
  }

  function closeEditor() {
    if (saving) return;
    setSelectedStore(null);
    setForm(emptyForm);
  }

  async function saveStore(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedStore) return;

    if (!form.name.trim() || !form.address.trim() || !form.city.trim() || !form.pincode.trim()) {
      setError("Name, address, city, and pincode are required.");
      return;
    }

    const latitude = form.latitude.trim() === "" ? null : Number(form.latitude);
    const longitude = form.longitude.trim() === "" ? null : Number(form.longitude);

    if (
      (latitude !== null && (!Number.isFinite(latitude) || latitude < -90 || latitude > 90)) ||
      (longitude !== null && (!Number.isFinite(longitude) || longitude < -180 || longitude > 180))
    ) {
      setError("Enter valid coordinates. Latitude must be between -90 and 90; longitude between -180 and 180.");
      return;
    }

    const payload: AdminStoreUpdatePayload = {
      name: form.name.trim(),
      address: form.address.trim(),
      city: form.city.trim(),
      pincode: form.pincode.trim(),
      latitude,
      longitude,
      is_active: form.is_active,
    };

    setSaving(true);
    setError("");
    setNotice("");

    try {
      await adminApi.updateStore(selectedStore.id, payload);
      setNotice(`Store "${form.name.trim()}" updated successfully.`);
      setSelectedStore(null);
      await loadStores();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update store.");
    } finally {
      setSaving(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-blue-600">Administration</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Store Management</h1>
          <p className="mt-1 text-sm text-slate-500">
            View store details and manage store information and availability.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void loadStores()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {notice && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          {notice}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Stores matching filters</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{total}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Current page</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{page + 1} / {totalPages}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm text-slate-500">Stores displayed</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{stores.length}</p>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            placeholder="Search by store name, city, address, or pincode"
            className="w-full rounded-lg border border-slate-300 py-2 pl-10 pr-3 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value as StatusFilter);
            setPage(0);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-blue-500"
        >
          <option value="all">All stores</option>
          <option value="active">Active stores</option>
          <option value="inactive">Inactive stores</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <div className="p-10 text-center text-sm text-slate-500">Loading stores...</div>
        ) : stores.length === 0 ? (
          <div className="p-10 text-center">
            <Store className="mx-auto text-slate-300" size={36} />
            <p className="mt-3 font-medium text-slate-700">No stores found</p>
            <p className="mt-1 text-sm text-slate-500">Try changing your search or status filter.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-3">Store</th>
                    <th className="px-5 py-3">Location</th>
                    <th className="px-5 py-3">Pincode</th>
                    <th className="px-5 py-3">Status</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {stores.map((store) => (
                    <tr key={store.id} className="hover:bg-slate-50">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                            <Store size={18} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900">{store.name}</p>
                            <p className="text-xs text-slate-500">Store #{store.id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        <div className="flex items-center gap-1.5">
                          <MapPin size={14} className="shrink-0 text-slate-400" />
                          <span>{store.city}</span>
                        </div>
                        <p className="mt-1 max-w-xs truncate text-xs text-slate-400">{store.address}</p>
                      </td>
                      <td className="px-5 py-4 text-slate-600">{store.pincode}</td>
                      <td className="px-5 py-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          store.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-100 text-slate-600"
                        }`}>
                          {store.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <button
                          type="button"
                          onClick={() => void openStore(store.id)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <Pencil size={14} />
                          View / Edit
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3">
              <p className="text-xs text-slate-500">
                Showing {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + stores.length} of {total}
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.max(0, current - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setPage((current) => Math.min(totalPages - 1, current + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-slate-300 p-2 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  aria-label="Next page"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {selectedStore && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/50 p-4">
          <div className="my-8 w-full max-w-2xl rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Edit store</h2>
                <p className="text-xs text-slate-500">Store #{selectedStore.id}</p>
              </div>
              <button
                type="button"
                onClick={closeEditor}
                disabled={saving}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"
                aria-label="Close editor"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={(event) => void saveStore(event)} className="space-y-4 p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-1 text-sm font-medium text-slate-700">
                  Store name *
                  <input
                    required
                    value={form.name}
                    onChange={(event) => updateForm("name", event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>

                <label className="space-y-1 text-sm font-medium text-slate-700">
                  City *
                  <input
                    required
                    value={form.city}
                    onChange={(event) => updateForm("city", event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>

                <label className="space-y-1 text-sm font-medium text-slate-700 sm:col-span-2">
                  Address *
                  <textarea
                    required
                    rows={2}
                    value={form.address}
                    onChange={(event) => updateForm("address", event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>

                <label className="space-y-1 text-sm font-medium text-slate-700">
                  Pincode *
                  <input
                    required
                    value={form.pincode}
                    onChange={(event) => updateForm("pincode", event.target.value)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>

                <div className="hidden sm:block" />

                <label className="space-y-1 text-sm font-medium text-slate-700">
                  Latitude
                  <input
                    type="number"
                    step="any"
                    value={form.latitude}
                    onChange={(event) => updateForm("latitude", event.target.value)}
                    placeholder="Optional"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>

                <label className="space-y-1 text-sm font-medium text-slate-700">
                  Longitude
                  <input
                    type="number"
                    step="any"
                    value={form.longitude}
                    onChange={(event) => updateForm("longitude", event.target.value)}
                    placeholder="Optional"
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 font-normal outline-none focus:border-blue-500"
                  />
                </label>
              </div>

              <label className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(event) => updateForm("is_active", event.target.checked)}
                  className="h-4 w-4 accent-blue-600"
                />
                <span>
                  <span className="block font-medium">Store is active</span>
                  <span className="text-xs text-slate-500">Inactive stores are retained but unavailable for active operations.</span>
                </span>
              </label>

              <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={closeEditor}
                  disabled={saving}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}