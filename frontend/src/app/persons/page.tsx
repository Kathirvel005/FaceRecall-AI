"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchPersons, deletePerson } from "../../services/api";
import { Person } from "../../types";

export default function PersonsPage() {
  const [persons, setPersons] = useState<Person[]>([]);
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadPersons = async (query?: string) => {
    setLoading(true);
    try {
      const data = await fetchPersons(query);
      setPersons(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPersons();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadPersons(search);
  };

  const handleDelete = async (person: Person) => {
    if (!confirm(`Are you sure you want to delete ${person.name} (${person.student_id}) and remove all biometric embeddings?`)) {
      return;
    }
    setDeletingId(person.id);
    try {
      await deletePerson(person.id);
      await loadPersons(search);
    } catch (err) {
      alert("Failed to delete person: " + err);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-gray-800">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Registered Student Directory</h2>
          <p className="text-sm text-gray-400">
            View, search, manage enrolled identities, and examine biometric sample counts
          </p>
        </div>
        <Link
          href="/persons/register"
          className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 text-white rounded-lg text-sm font-medium shadow-md shadow-cyan-900/20 transition-all flex items-center space-x-2"
        >
          <span>➕ Enroll New Student</span>
        </Link>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-2 max-w-md">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by student ID, name, or department..."
          className="flex-1 bg-gray-900/80 border border-gray-800 rounded-lg px-3.5 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm font-medium transition"
        >
          Search
        </button>
      </form>

      {/* Persons Table */}
      <div className="glass-card rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-[#0e1424] text-xs uppercase tracking-wider text-gray-400 border-b border-gray-800">
              <tr>
                <th className="px-6 py-3.5">Student</th>
                <th className="px-6 py-3.5">Student ID</th>
                <th className="px-6 py-3.5">Department / Class</th>
                <th className="px-6 py-3.5">Face Samples</th>
                <th className="px-6 py-3.5">Enrolled Date</th>
                <th className="px-6 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/80">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    Loading registered students...
                  </td>
                </tr>
              ) : persons.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                    <span className="text-3xl block mb-2">👥</span>
                    No registered students found. Click "Enroll New Student" to register a student.
                  </td>
                </tr>
              ) : (
                persons.map((person) => (
                  <tr key={person.id} className="hover:bg-gray-800/30 transition">
                    <td className="px-6 py-4 font-medium text-white flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-full bg-cyan-900/40 border border-cyan-700/50 flex items-center justify-center text-xs text-cyan-300 font-bold">
                        {person.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div>{person.name}</div>
                        {person.email && (
                          <div className="text-xs text-gray-500">{person.email}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 font-mono text-cyan-400 text-xs">
                      {person.student_id}
                    </td>
                    <td className="px-6 py-4 text-gray-300">
                      {person.department || "—"} {person.class_name ? `(${person.class_name})` : ""}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {person.samples_count} embeddings
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-xs">
                      {new Date(person.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(person)}
                        disabled={deletingId === person.id}
                        className="px-3 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded text-xs font-medium transition"
                      >
                        {deletingId === person.id ? "Purging..." : "Delete"}
                      </button>
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
