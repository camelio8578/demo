import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({ baseURL: API_BASE });

// ---- Creators ----
export const getCreators = () => api.get('/api/v1/creators');
export const getCreator = (id: string) => api.get(`/api/v1/creators/${id}`);
export const createCreator = (data: any) => api.post('/api/v1/creators', data);
export const updateCreator = (id: string, data: any) => api.put(`/api/v1/creators/${id}`, data);

// ---- Videos ----
export const getVideos = (params?: any) => api.get('/api/v1/videos', { params });
export const getVideo = (id: string) => api.get(`/api/v1/videos/${id}`);
export const ingestVideo = (data: any) => api.post('/api/v1/ingest', data);

// ---- Candidates ----
export const getCandidates = (videoId: string) =>
  api.get(`/api/v1/videos/${videoId}/candidates`);
export const getCandidate = (id: string) => api.get(`/api/v1/candidates/${id}`);
export const updateCandidateStatus = (id: string, status: string, notes?: string) =>
  api.put(`/api/v1/candidates/${id}/status`, { status, notes });
export const renderCandidate = (id: string) =>
  api.post(`/api/v1/candidates/${id}/render`);
export const generateCopy = (id: string) =>
  api.post(`/api/v1/candidates/${id}/copy`);

// ---- Assets ----
export const getAsset = (id: string) => api.get(`/api/v1/assets/${id}`);
export const rerenderAsset = (id: string) =>
  api.post(`/api/v1/assets/${id}/rerender`);

// ---- Publishing ----
export const getJobs = (params?: any) => api.get('/api/v1/jobs', { params });
export const getJob = (id: string) => api.get(`/api/v1/jobs/${id}`);
export const createJob = (data: any) => api.post('/api/v1/jobs', data);
export const retryJob = (id: string) => api.post(`/api/v1/jobs/${id}/retry`);
export const cancelJob = (id: string) => api.delete(`/api/v1/jobs/${id}`);

// ---- Analytics ----
export const getAnalytics = (jobId: string) =>
  api.get(`/api/v1/analytics/jobs/${jobId}`);
export const getAnalyticsSummary = () => api.get('/api/v1/analytics/summary');
export const triggerAnalyticsIngest = (jobId: string) =>
  api.post(`/api/v1/analytics/ingest/${jobId}`);

// ---- Review ----
export const getReviewQueue = () => api.get('/api/v1/review/queue');
export const getReviewTasks = (params?: any) =>
  api.get('/api/v1/review/tasks', { params });
export const updateReviewTask = (id: string, data: any) =>
  api.put(`/api/v1/review/tasks/${id}`, data);
export const createReviewTask = (data: any) =>
  api.post('/api/v1/review/tasks', data);

// ---- Settings ----
export const getSettings = () => api.get('/api/v1/settings');
export const updateSetting = (key: string, value: any) =>
  api.put(`/api/v1/settings/${key}`, { value });

// ---- Health ----
export const getHealth = () => api.get('/api/v1/health');
export const getWorkerHealth = () => api.get('/api/v1/health/workers');
export const getQueueStatus = () => api.get('/api/v1/jobs/queue-status');
