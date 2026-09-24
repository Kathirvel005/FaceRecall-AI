"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchHealth } from "../services/api";

export default function Navigation() {
  const pathname = usePathname();
  const [apiOnline, setApiOnline] = useState<boolean>(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const res = await fetchHealth();
        setApiOnline(res.status === "HEALTHY");
      } catch {
        setApiOnline(false);
      }
    };
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { href: "/", label: "Overview", icon: "📊" },
    { href: "/recognition", label: "Live Recognition", icon: "🎥" },
    { href: "/persons", label: "Student Registry", icon: "👥" },
    { href: "/persons/register", label: "Enroll Student", icon: "➕" },
    { href: "/events", label: "Audit Events", icon: "📜" },
    { href: "/system", label: "System Diagnostics", icon: "⚙️" },
  ];

  return (
    <aside className="w-64 bg-[#0d1322] border-r border-gray-800/80 flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="p-5 border-b border-gray-800/80 flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-cyan-900/30">
            👁️
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-white">Classroom Vision</h1>
            <p className="text-xs text-gray-400">Multi-Face Identity</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center space-x-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm"
                    : "text-gray-400 hover:text-gray-100 hover:bg-gray-800/50"
                }`}
              >
                <span className="text-base">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Backend Status Footer */}
      <div className="p-4 border-t border-gray-800/80 bg-[#090e1a]/60">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Backend API</span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full font-medium ${
              apiOnline
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                apiOnline ? "bg-emerald-400 animate-pulse" : "bg-rose-400"
              }`}
            />
            {apiOnline ? "Connected" : "Offline"}
          </span>
        </div>
      </div>
    </aside>
  );
}
