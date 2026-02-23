import { useState, useEffect, useCallback } from "react";
import { api } from "./api/client";
import DocumentsTable from "./components/DocumentsTable";
import Filters from "./components/Filters";
import BatchProcessor from "./components/BatchProcessor";

const PAGE_SIZE = 10;
const INITIAL_FILTERS = {
  invoice_type: "",
  status: "",
  min_amount: "",
  max_amount: "",
  start_date: "",
  end_date: "",
};

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const fetchDocuments = useCallback(async (currentSkip, currentFilters) => {
    setLoading(true);
    setError(null);
    try {
      // Convert datetime-local to ISO-8601 with timezone
      const params = {
        skip: currentSkip,
        limit: PAGE_SIZE,
        ...Object.fromEntries(
          Object.entries(currentFilters).filter(([, v]) => v !== "")
        ),
      };
      if (params.start_date) params.start_date = new Date(params.start_date).toISOString();
      if (params.end_date) params.end_date = new Date(params.end_date).toISOString();

      const data = await api.getDocuments(params);
      setDocuments(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Re-fetch whenever skip or filters change
  useEffect(() => {
    fetchDocuments(skip, filters);
  }, [skip, filters, fetchDocuments]);

  const handleFilterChange = (newFilters) => {
    setSkip(0); // reset to first page on filter change
    setFilters(newFilters);
    setSelectedIds(new Set());
  };

  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleBatchComplete = () => {
    setSelectedIds(new Set());
    fetchDocuments(skip, filters); // refresh table after job completes
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white tracking-tight">Billing Documents</h1>
            <p className="text-xs text-gray-500">duppla · Financial document management</p>
          </div>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-indigo-400 hover:text-indigo-300 transition"
          >
            API Docs →
          </a>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-6">

        {/* Filters */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Filters</h2>
          <Filters filters={filters} onChange={handleFilterChange} />
        </section>

        {/* Batch processor */}
        <section className="p-4 rounded-xl bg-gray-900/40 border border-gray-800">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500 mb-3">Batch Processing</h2>
          <BatchProcessor
            selectedIds={selectedIds}
            onComplete={handleBatchComplete}
          />
        </section>

        {/* Table */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">Documents</h2>
            {loading && (
              <span className="text-xs text-indigo-400 flex items-center gap-1.5">
                <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </span>
            )}
          </div>

          {error ? (
            <div className="rounded-xl border border-red-700 bg-red-950/30 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          ) : (
            <DocumentsTable
              documents={documents}
              total={total}
              skip={skip}
              limit={PAGE_SIZE}
              onPageChange={setSkip}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
            />
          )}
        </section>
      </main>
    </div>
  );
}
