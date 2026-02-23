const TYPES = ["invoice", "receipt", "proof of payment"];
const STATUSES = ["draft", "pending", "approved", "rejected"];

export default function Filters({ filters, onChange }) {
    const set = (key) => (e) => onChange({ ...filters, [key]: e.target.value });

    const inputCls = "w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder-gray-600";
    const selectCls = `${inputCls} appearance-none`;

    return (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <select value={filters.invoice_type || ""} onChange={set("invoice_type")} className={selectCls}>
                <option value="">All types</option>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>

            <select value={filters.status || ""} onChange={set("status")} className={selectCls}>
                <option value="">All statuses</option>
                {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>

            <input
                type="number"
                placeholder="Min amount"
                value={filters.min_amount || ""}
                onChange={set("min_amount")}
                className={inputCls}
            />
            <input
                type="number"
                placeholder="Max amount"
                value={filters.max_amount || ""}
                onChange={set("max_amount")}
                className={inputCls}
            />
            <input
                type="datetime-local"
                value={filters.start_date || ""}
                onChange={set("start_date")}
                className={inputCls}
                title="From date"
            />
            <input
                type="datetime-local"
                value={filters.end_date || ""}
                onChange={set("end_date")}
                className={inputCls}
                title="To date"
            />
        </div>
    );
}
