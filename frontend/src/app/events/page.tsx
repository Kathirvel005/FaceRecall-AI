"use client";

import { useEffect, useState } from "react";
import { fetchEvents } from "../../services/api";
import { RecognitionEvent } from "../../types";

export default function EventsPage() {
  const [events, setEvents] = useState<RecognitionEvent[]>([]);
  const [filter, setFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState<boolean>(true);

  const loadEvents = async () => {
    setLoading(true);
    try {
      const data = await fetchEvents(100);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, []);

  const filteredEvents = events.filter((e) => {
    if (filter === "ALL") return true;
    return e.status === filter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Recognition Audit Log</h2>
          <p className="text-sm text-gray-400">
            Chronological audit trail of multi-face identification and temporal decisions
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {["ALL", "KNOWN", "UNKNOWN"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                filter === f
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "bg-gray-800/80 text-gray-400 hover:text-white"
              }`}
            >
              {f}
            </button>
          ))}
          <button
            onClick={loadEvents}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium transition"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Events Table */}
      <div className="glass-card rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#0e1424] text-xs uppercase tracking-wider text-gray-400 border-b border-gray-800">
              <tr>
                <th className="px-6 py-3.5">Timestamp</th>
                <th className="px-6 py-3.5">Identity</th>
                <th className="px-6 py-3.5">Student ID</th>
                <th className="px-6 py-3.5">Track ID</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Similarity</th>
                <th className="px-6 py-3.5">Quality</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/80">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                    Loading events...
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                    No recognition events logged matching current filter.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt) => (
                  <tr key={evt.id} className="hover:bg-gray-800/30 transition text-xs">
                    <td className="px-6 py-3.5 text-gray-400 font-mono">
                      {new Date(evt.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-3.5 font-medium text-white">
                      {evt.name}
                    </td>
                    <td className="px-6 py-3.5 text-cyan-400 font-mono">
                      {evt.student_id || "—"}
                    </td>
                    <td className="px-6 py-3.5 text-gray-400 font-mono">
                      #{evt.track_id}
                    </td>
                    <td className="px-6 py-3.5">
                      <span
                        className={`inline-block px-2 py-0.5 rounded font-mono font-medium ${
                          evt.status === "KNOWN"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {evt.status}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 font-mono text-white">
                      {(evt.similarity * 100).toFixed(1)}%
                    </td>
                    <td className="px-6 py-3.5 font-mono text-gray-400">
                      {(evt.quality * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
