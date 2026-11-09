
import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Search,
  ShieldCheck,
  UserCheck,
  UserX,
} from "lucide-react";

import { useAuth } from "../../auth/AuthContext";
import {
  adminApi,
  type User,
  type UserRole,
} from "../../lib/api";

const PAGE_SIZE = 10;

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();

  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const data = await adminApi.getUsers({
        search: search.trim() || undefined,
        role: (role || undefined) as UserRole | undefined,
        is_active:
          status === "active"
            ? true
            : status === "inactive"
              ? false
              : undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });

      setUsers(data.users);
      setTotal(data.total);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load users.",
      );
    } finally {
      setLoading(false);
    }
  }, [search, role, status, page]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const updateUser = async (
    target: User,
    payload: { role?: UserRole; is_active?: boolean },
  ) => {
    if (target.id === currentUser?.id) {
      setError("You cannot modify your own administrator account.");
      return;
    }

    const description = payload.role
      ? `change ${target.full_name}'s role to ${payload.role}`
      : `${payload.is_active ? "activate" : "deactivate"} ${target.full_name}'s account`;

    if (!window.confirm(`Are you sure you want to ${description}?`)) {
      return;
    }

    setUpdatingId(target.id);
    setError("");
    setNotice("");

    try {
      await adminApi.updateUser(target.id, payload);
      setNotice("User updated successfully.");
      await loadUsers();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to update user.",
      );
    } finally {
      setUpdatingId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-emerald-700">
            Administration
          </p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">
            User Management
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Manage platform accounts, roles and access.
          </p>
        </div>

        <button
          onClick={() => void loadUsers()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Total matching users</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {total.toLocaleString("en-IN")}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Users on this page</p>
          <p className="mt-2 text-2xl font-bold text-slate-900">
            {users.length}
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-sm text-slate-500">Current administrator</p>
          <p className="mt-2 truncate text-base font-semibold text-slate-900">
            {currentUser?.full_name ?? "Administrator"}
          </p>
        </div>
      </div>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          Search and filters
        </h2>

        <div className="mt-4 grid gap-3 md:grid-cols-[1fr_190px_190px]">
          <div className="relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(0);
              }}
              placeholder="Search name or email..."
              className="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
            />
          </div>

          <select
            value={role}
            onChange={(event) => {
              setRole(event.target.value);
              setPage(0);
            }}
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-600"
          >
            <option value="">All roles</option>
            <option value="customer">Customer</option>
            <option value="pharmacist">Pharmacist</option>
            <option value="admin">Administrator</option>
          </select>

          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(0);
            }}
            className="rounded-xl border border-slate-300 px-3 py-2.5 text-sm outline-none focus:border-emerald-600"
          >
            <option value="">All account statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
          </select>
        </div>
      </section>

      {error && (
        <div className="mt-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <AlertCircle size={19} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {notice && (
        <div className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          {notice}
        </div>
      )}

      <section className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5">
          <h2 className="font-semibold text-slate-900">Platform users</h2>
          <span className="text-sm text-slate-500">
            {total === 0
              ? "No users found"
              : `${page * PAGE_SIZE + 1}–${Math.min(
                  (page + 1) * PAGE_SIZE,
                  total,
                )} of ${total}`}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center gap-3 p-10 text-sm text-slate-500">
            <RefreshCw size={18} className="animate-spin" />
            Loading users...
          </div>
        ) : users.length === 0 ? (
          <div className="p-10 text-center">
            <ShieldCheck size={32} className="mx-auto text-slate-300" />
            <p className="mt-3 font-medium text-slate-700">
              No matching users
            </p>
            <p className="mt-1 text-sm text-slate-500">
              Try changing your search or filters.
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-5 py-4">User</th>
                    <th className="px-5 py-4">Phone</th>
                    <th className="px-5 py-4">Role</th>
                    <th className="px-5 py-4">Status</th>
                    <th className="px-5 py-4">Registered</th>
                    <th className="px-5 py-4">Actions</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100">
                  {users.map((target) => {
                    const isSelf = target.id === currentUser?.id;
                    const isUpdating = updatingId === target.id;

                    return (
                      <tr key={target.id} className="hover:bg-slate-50">
                        <td className="px-5 py-4">
                          <p className="font-semibold text-slate-900">
                            {target.full_name}
                            {isSelf && (
                              <span className="ml-2 text-xs font-medium text-emerald-700">
                                You
                              </span>
                            )}
                          </p>
                          <p className="mt-1 text-xs text-slate-500">
                            {target.email}
                          </p>
                        </td>

                        <td className="px-5 py-4 text-slate-600">
                          {target.phone || "—"}
                        </td>

                        <td className="px-5 py-4">
                          <select
                            value={target.role}
                            disabled={isSelf || isUpdating}
                            onChange={(event) =>
                              void updateUser(target, {
                                role: event.target.value as UserRole,
                              })
                            }
                            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm capitalize disabled:cursor-not-allowed disabled:bg-slate-100 disabled:opacity-60"
                            aria-label={`Change role for ${target.full_name}`}
                          >
                            <option value="customer">Customer</option>
                            <option value="pharmacist">Pharmacist</option>
                            <option value="admin">Administrator</option>
                          </select>
                        </td>

                        <td className="px-5 py-4">
                          <span
                            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                              target.is_active
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-rose-50 text-rose-700"
                            }`}
                          >
                            {target.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-slate-600">
                          {new Date(target.created_at).toLocaleDateString(
                            "en-IN",
                            {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            },
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <button
                            disabled={isSelf || isUpdating}
                            onClick={() =>
                              void updateUser(target, {
                                is_active: !target.is_active,
                              })
                            }
                            className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${
                              target.is_active
                                ? "bg-rose-50 text-rose-700 hover:bg-rose-100"
                                : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                            }`}
                          >
                            {target.is_active ? (
                              <UserX size={15} />
                            ) : (
                              <UserCheck size={15} />
                            )}
                            {isUpdating
                              ? "Saving..."
                              : target.is_active
                                ? "Deactivate"
                                : "Activate"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between gap-4 border-t border-slate-200 p-4">
              <p className="text-xs text-slate-500">
                Page {page + 1} of {totalPages}
              </p>

              <div className="flex gap-2">
                <button
                  disabled={page === 0 || loading}
                  onClick={() => setPage((current) => current - 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-40"
                >
                  <ChevronLeft size={16} />
                  Previous
                </button>

                <button
                  disabled={page + 1 >= totalPages || loading}
                  onClick={() => setPage((current) => current + 1)}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 disabled:opacity-40"
                >
                  Next
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      <p className="mt-5 text-xs text-slate-500">
        Administrator accounts cannot change their own role or deactivate
        themselves. All successful updates are recorded in the audit log.
      </p>
    </main>
  );
}
