const STATUS_STYLES = {
    draft: "bg-gray-700 text-gray-200",
    pending: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40",
    approved: "bg-green-500/20 text-green-300 border border-green-500/40",
    rejected: "bg-red-500/20 text-red-300 border border-red-500/40",
    processing: "bg-blue-500/20 text-blue-300 border border-blue-500/40",
    completed: "bg-green-500/20 text-green-300 border border-green-500/40",
    failed: "bg-red-500/20 text-red-300 border border-red-500/40",
};

export default function StatusBadge({ status }) {
    return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[status] ?? "bg-gray-700 text-gray-300"}`}>
            {status}
        </span>
    );
}
