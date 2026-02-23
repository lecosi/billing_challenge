// Centralised API client — injects the X-API-Key header on every request.
// In production it uses /api to go through the Nginx proxy, avoiding CORS/IP issues.
const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY || "ccf26ad1-c694-463a-834a-7e666d94424b";

async function request(path, options = {}) {
    const res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
            ...options.headers,
        },
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Request failed");
    }
    return res.json();
}

export const api = {
    // Documents
    getDocuments: (params = {}) => {
        const qs = new URLSearchParams(
            Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))
        ).toString();
        return request(`/documents${qs ? `?${qs}` : ""}`);
    },

    // Batch processing
    processBatch: (documentIds) =>
        request("/documents/batch/process", {
            method: "POST",
            body: JSON.stringify({ document_ids: documentIds }),
        }),

    // Job status
    getJob: (jobId) => request(`/jobs/${jobId}`),
};
