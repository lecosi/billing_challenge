import StatusBadge from "./StatusBadge";

function formatDate(iso) {
    return new Date(iso).toLocaleString("es-CO", {
        dateStyle: "short",
        timeStyle: "short",
    });
}

function formatAmount(amount) {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(amount);
}

export default function DocumentsTable({ documents, total, skip, limit, onPageChange, selectedIds, onToggleSelect }) {
    const totalPages = Math.ceil(total / limit);
    const currentPage = Math.floor(skip / limit) + 1;

    return (
        <div>
            <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="min-w-full text-sm">
                    <thead className="bg-gray-900 text-gray-400 text-xs uppercase tracking-wider">
                        <tr>
                            <th className="px-4 py-3 text-left w-8">
                                <span className="sr-only">Select</span>
                            </th>
                            <th className="px-4 py-3 text-left">ID</th>
                            <th className="px-4 py-3 text-left">Type</th>
                            <th className="px-4 py-3 text-right">Amount</th>
                            <th className="px-4 py-3 text-center">Status</th>
                            <th className="px-4 py-3 text-left">Created</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                        {documents.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                                    No documents found.
                                </td>
                            </tr>
                        ) : (
                            documents.map((doc) => {
                                const isDraft = doc.status === "draft";
                                const isSelected = selectedIds.has(doc.id);
                                return (
                                    <tr
                                        key={doc.id}
                                        className={`transition-colors ${isSelected ? "bg-indigo-950/40" : "hover:bg-gray-900/60"}`}
                                    >
                                        <td className="px-4 py-3">
                                            {isDraft && (
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => onToggleSelect(doc.id)}
                                                    className="rounded border-gray-600 bg-gray-800 text-indigo-500 focus:ring-indigo-500"
                                                />
                                            )}
                                        </td>
                                        <td className="px-4 py-3 font-mono text-xs text-gray-400">{doc.id.slice(0, 8)}…</td>
                                        <td className="px-4 py-3 capitalize">{doc.invoice_type}</td>
                                        <td className="px-4 py-3 text-right font-medium">{formatAmount(doc.amount)}</td>
                                        <td className="px-4 py-3 text-center">
                                            <StatusBadge status={doc.status} />
                                        </td>
                                        <td className="px-4 py-3 text-gray-400">{formatDate(doc.created_at)}</td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 text-sm text-gray-400">
                <span>{total} document{total !== 1 ? "s" : ""} total</span>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => onPageChange(skip - limit)}
                        disabled={skip === 0}
                        className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                        ← Prev
                    </button>
                    <span className="px-2">
                        Page {currentPage} / {totalPages || 1}
                    </span>
                    <button
                        onClick={() => onPageChange(skip + limit)}
                        disabled={skip + limit >= total}
                        className="px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition"
                    >
                        Next →
                    </button>
                </div>
            </div>
        </div>
    );
}
