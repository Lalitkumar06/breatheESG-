import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Inject auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ─── Auth ───────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (username: string, password: string) =>
    api.post('/auth/login/', { username, password }),
  logout: () => api.post('/auth/logout/'),
  me: () => api.get('/auth/me/'),
};

// ─── Dashboard ───────────────────────────────────────────────────────────────
export const dashboardAPI = {
  summary: () => api.get('/dashboard/summary/'),
};

// ─── Ingestion Jobs ───────────────────────────────────────────────────────────
export const jobsAPI = {
  list: () => api.get('/jobs/'),
  detail: (id: string) => api.get(`/jobs/${id}/`),
  upload: (file: File, sourceType: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('source_type', sourceType);
    return api.post('/ingest/upload/', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ─── Emission Records ─────────────────────────────────────────────────────────
export const recordsAPI = {
  list: (params?: Record<string, string>) =>
    api.get('/records/', { params }),
  detail: (id: string) => api.get(`/records/${id}/`),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/records/${id}/`, data),
  approve: (id: string, notes?: string) =>
    api.post(`/records/${id}/approve/`, { notes }),
  reject: (id: string, reason: string) =>
    api.post(`/records/${id}/reject/`, { reason }),
  flag: (id: string, reason: string) =>
    api.post(`/records/${id}/flag/`, { reason }),
  delete: (id: string) =>
    api.delete(`/records/${id}/`),
  bulkApprove: (ids: string[]) =>
    api.post('/records/bulk-approve/', { ids }),
  history: (id: string) => api.get(`/records/${id}/history/`),
};

export default api;
