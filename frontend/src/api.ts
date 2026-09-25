import axios from 'axios';

/**
 * Resolves the backend origin:
 *  1. VITE_API_ORIGIN env override (set in .env / .env.production)
 *  2. Proxied preview environments (host pattern "{port}-{sandbox}.e2b.app")
 *     -> swap the port label to the backend port 8000
 *  3. Local development -> http://localhost:8000
 */
function resolveApiOrigin(): string {
  const explicit = import.meta.env.VITE_API_ORIGIN;
  if (explicit) return explicit;

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const proxyMatch = host.match(/^(\d+)-(.+)$/);
    if (proxyMatch && proxyMatch[1] !== '8000') {
      return `${window.location.protocol}//8000-${proxyMatch[2]}`;
    }
    if (proxyMatch && proxyMatch[1] === '8000') {
      return `${window.location.protocol}//${host}`;
    }
  }
  return 'http://localhost:8000';
}

export const API_ORIGIN = resolveApiOrigin();

const api = axios.create({
  baseURL: `${API_ORIGIN}/api/v1`,
  headers: {
    'Content-Type': 'application/json'
  }
});

export default api;
