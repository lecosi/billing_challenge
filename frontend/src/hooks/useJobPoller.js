import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api/client";

const POLL_INTERVAL_MS = 2000;
const TERMINAL_STATES = new Set(["completed", "failed"]);

/**
 * Polls GET /jobs/{jobId} every POLL_INTERVAL_MS until the job
 * reaches a terminal state (completed | failed) or is cancelled.
 *
 * Returns { job, isPolling, error }.
 */
export function useJobPoller(jobId) {
    const [job, setJob] = useState(null);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState(null);
    const intervalRef = useRef(null);

    const stop = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
        setIsPolling(false);
    }, []);

    useEffect(() => {
        if (!jobId) return;

        setIsPolling(true);
        setError(null);
        setJob(null);

        const poll = async () => {
            try {
                const data = await api.getJob(jobId);
                setJob(data);
                if (TERMINAL_STATES.has(data.status)) stop();
            } catch (err) {
                setError(err.message);
                stop();
            }
        };

        poll(); // immediate first call
        intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

        return stop; // cleanup on unmount or jobId change
    }, [jobId, stop]);

    return { job, isPolling, error };
}
