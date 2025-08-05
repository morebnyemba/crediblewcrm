// src/lib/api.js
import { toast } from 'sonner';

// --- DEBUGGING: Log the environment variable to check if it's loaded ---
console.log("VITE_API_BASE_URL from import.meta.env:", import.meta.env.VITE_API_BASE_URL);
// --- END DEBUGGING ---

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://crmbackend.lifeinternationalministries.com';
const getAuthToken = () => localStorage.getItem('accessToken');

export async function apiCall(endpoint, { method = 'GET', body = null, isPaginatedFallback = false } = {}) {
  const token = getAuthToken();
  const headers = {
    ...(!body || !(body instanceof FormData) && { 'Content-Type': 'application/json' }),
    ...(token && { 'Authorization': `Bearer ${token}` }),
  };
  const config = { method, headers, ...(body && !(body instanceof FormData) && { body: JSON.stringify(body) }) };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    if (!response.ok) {
      let errorData = { detail: `Request to ${endpoint} failed: ${response.status} ${response.statusText}` };
      try {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
          errorData = await response.json();
          if (response.status === 401 && (errorData.code === "token_not_valid" || errorData.detail?.includes("token not valid") || errorData.detail?.includes("Authentication credentials were not provided"))) {
            toast.error("Session expired or token invalid. Please log in again.", { id: `auth-error-${Date.now()}` });
            // A hard redirect is a simple way to handle expired sessions.
            window.location.href = '/login';
          }
        } else {
          errorData.detail = (await response.text()) || errorData.detail;
        }
      } catch (e) { console.error("Failed to parse error response for a failed request:", e); }

      const errorMessage = errorData.detail ||
                           (typeof errorData === 'object' && errorData !== null && !errorData.detail ?
                             Object.entries(errorData).map(([k,v])=>`${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(', ') : String(v)}`).join('; ') :
                             `API Error ${response.status}`);
      const err = new Error(errorMessage); err.data = errorData; err.isApiError = true; throw err;
    }
    if (response.status === 204 || (response.headers.get("content-length") || "0") === "0") {
      return isPaginatedFallback ? { results: [], count: 0, next: null, previous: null } : null;
    }
    const data = await response.json();
    if (isPaginatedFallback) {
      return { 
        results: data.results || (Array.isArray(data) ? data : []), 
        count: data.count === undefined ? (Array.isArray(data) ? data.length : 0) : data.count,
        next: data.next,
        previous: data.previous
      };
    }
    return data;
  } catch (error) {
    console.error(`API call to ${method} ${API_BASE_URL}${endpoint} failed:`, error);
    if (!error.isApiError || !error.message.includes("(toasted)")) {
        toast.error(error.message || 'An API error occurred. Check console.');
        error.message = (error.message || "") + " (toasted)";
    }
    throw error;
  }
}