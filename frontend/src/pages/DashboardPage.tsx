
import { Link } from "react-router-dom";
import {
  HeartPulse,
  LogOut,
  ClipboardList,
  FileText,
  Package,
  ShieldCheck,
  Users,
  Activity,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const isCustomer = user.role === "customer";
  const isPharmacist = user.role === "pharmacist";
//   const isAdmin = user.role === "admin";

  const roleTitle = isCustomer
    ? "Customer Dashboard"
    : isPharmacist
      ? "Pharmacist Dashboard"
      : "Administrator Dashboard";

  const description = isCustomer
    ? "Manage your prescriptions and medicine refills in one place."
    : isPharmacist
      ? "Review prescriptions and manage customer orders."
      : "Monitor and manage the MediFlow pharmacy platform.";

  const dashboardItems = isCustomer
    ? [
        {
          title: "My Prescriptions",
          description: "Upload and track prescription reviews.",
          icon: FileText,
          link: "/prescriptions",
        },
        {
          title: "My Orders",
          description: "View your medicine orders and their status.",
          icon: Package,
        },
        {
          title: "Refill Management",
          description: "Manage your recurring medicine refills.",
          icon: Activity,
        },
      ]
    : isPharmacist
      ? [
          {
            title: "Prescription Queue",
            description: "Review prescriptions submitted by customers.",
            icon: ClipboardList,
          },
          {
            title: "Order Management",
            description: "Review and manage pharmacy orders.",
            icon: Package,
          },
          {
            title: "Verification",
            description: "Verify medicines and prescription details.",
            icon: ShieldCheck,
          },
        ]
      : [
          {
            title: "User Management",
            description: "Manage customer and staff accounts.",
            icon: Users,
          },
          {
            title: "Store Management",
            description: "Manage pharmacy store information.",
            icon: Package,
          },
          {
            title: "Platform Overview",
            description: "Monitor platform activity and operations.",
            icon: Activity,
          },
        ];

  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link
            to="/"
            className="flex items-center gap-2 text-xl font-bold text-emerald-950"
          >
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-700 text-white">
              <HeartPulse size={22} />
            </span>
            MediFlow
          </Link>

          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            <LogOut size={17} />
            Sign out
          </button>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 py-10 sm:px-8">
        <div className="rounded-3xl bg-emerald-800 p-7 text-white sm:p-10">
          <p className="text-sm font-medium text-emerald-100">
            Welcome, {user.full_name}
          </p>

          <h1 className="mt-2 text-3xl font-semibold">
            {roleTitle}
          </h1>

          <p className="mt-3 max-w-xl text-sm leading-6 text-emerald-100">
            {description}
          </p>

          <div className="mt-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 text-xs font-medium">
            <ShieldCheck size={15} />
            Signed in as {user.role}
          </div>
        </div>

        <div className="mt-9">
          <h2 className="text-xl font-semibold text-slate-900">
            Your workspace
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Available features for your account.
          </p>

          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {dashboardItems.map((item) => {
              const Icon = item.icon;

              return (
                <article
                  key={item.title}
                  className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
                >
                 <div className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
                  <Icon size={22} />
                 </div>

                 <h3 className="mt-4 font-semibold text-slate-900">
                  {item.title}
                 </h3>

                 <p className="mt-2 text-sm leading-6 text-slate-500">
                  {item.description}
                 </p>

                 {item.link ? (
                  <Link
                    to={item.link}
                    className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-emerald-700 hover:text-emerald-900"
                  >
                    Open feature →
                  </Link>
                ) : (
                  <p className="mt-4 text-xs font-medium text-amber-700">
                    Feature implementation pending
                  </p>
                )}
              </article>
              );
            })}
          </div>
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="font-semibold text-slate-900">
            Account information
          </h2>

          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Full name</dt>
              <dd className="mt-1 font-medium text-slate-800">
                {user.full_name}
              </dd>
            </div>

            <div>
              <dt className="text-slate-500">Email address</dt>
              <dd className="mt-1 font-medium text-slate-800">
                {user.email}
              </dd>
            </div>

            <div>
              <dt className="text-slate-500">Account role</dt>
              <dd className="mt-1 font-medium capitalize text-slate-800">
                {user.role}
              </dd>
            </div>

            <div>
              <dt className="text-slate-500">Account status</dt>
              <dd className="mt-1 font-medium text-emerald-700">
                {user.is_active ? "Active" : "Inactive"}
              </dd>
            </div>
          </dl>
        </div>
      </section>
    </main>
  );
}
