import { useState } from "react";
import { api } from "../api/client";
import { useJobPoller } from "../hooks/useJobPoller";
import StatusBadge from "./StatusBadge";

function Spinner() {
    return (
        <svg className="animate-spin h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
    );
}

export default function BatchProcessor({ selectedIds, onComplete }) {
    const [jobId, setJobId] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);

    const { job, isPolling, error: pollError } = useJobPoller(jobId);

    const handleProcess = async () => {
        if (selectedIds.size === 0) return;
        setSubmitting(true);
        setSubmitError(null);
        setJobId(null);

        try {
            const res = await api.processBatch([...selectedIds]);
            setJobId(res.job_id);
        } catch (err) {
            setSubmitError(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    // Notify parent when job completes so it can refresh the table
    const isCompleted = job?.status === "completed";
    const isFailed = job?.status === "failed";

    if (isCompleted && onComplete) {
        // defer to avoid calling during render
        setTimeout(onComplete, 0);
    }

    return (
        <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
                <button
                    onClick={handleProcess}
                    disabled={selectedIds.size === 0 || submitting || isPolling}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
                >
                    {(submitting || isPolling) && <Spinner />}
                    {submitting
                        ? "Submitting…"
                        : isPolling
                            ? "Processing…"
                            : `Process ${selectedIds.size} document${selectedIds.size !== 1 ? "s" : ""}`}
                </button>

                {selectedIds.size === 0 && (
                    <span className="text-xs text-gray-500">Select DRAFT documents to process</span>
                )}
            </div>

            {/* Job status panel */}
            {jobId && (
                <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border text-sm
          ${isFailed ? "border-red-700 bg-red-950/40" : isCompleted ? "border-green-700 bg-green-950/40" : "border-indigo-700 bg-indigo-950/40"}`}>
                    {isPolling && <Spinner />}
                    <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                            <span className="text-gray-400 text-xs font-mono truncate">Job {jobId.slice(0, 8)}…</span>
                            {job && <StatusBadge status={job.status} />}
                        </div>
                        {isFailed && (
                            <span className="text-red-400 text-xs">{job?.error_message || "Job failed"}</span>
                        )}
                        {isCompleted && (
                            <span className="text-green-400 text-xs">
                                ✓ Completed — table refreshed
                            </span>
                        )}
                        {isPolling && (
                            <span className="text-indigo-300 text-xs">Polling every 2s…</span>
                        )}
                    </div>
                </div>
            )}

            {submitError && (
                <p className="text-red-400 text-xs">{submitError}</p>
            )}
            {pollError && (
                <p className="text-red-400 text-xs">Polling error: {pollError}</p>
            )}
        </div>
    );
}
