import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
});

// ---- Complaints ----

export async function uploadImage(file, latitude, longitude, source = 'citizen') {
  const form = new FormData();
  form.append('file', file);
  form.append('latitude', latitude);
  form.append('longitude', longitude);
  form.append('source', source);
  const { data } = await api.post('/complaints/upload', form);
  return data;
}

export async function fetchComplaints({ page = 1, perPage = 20, status, severity, issueType, sortBy = 'created_at', sortOrder = 'desc' } = {}) {
  const params = { page, per_page: perPage, sort_by: sortBy, sort_order: sortOrder };
  if (status) params.status = status;
  if (severity) params.severity = severity;
  if (issueType) params.issue_type = issueType;
  const { data } = await api.get('/complaints/', { params });
  return data;
}

export async function fetchComplaint(id) {
  const { data } = await api.get(`/complaints/${id}`);
  return data;
}

export async function updateComplaintStatus(id, status, assignedTo, department, notes) {
  const body = { status };
  if (assignedTo) body.assigned_to = assignedTo;
  if (department) body.department = department;
  if (notes) body.notes = notes;
  const { data } = await api.patch(`/complaints/${id}/status`, body);
  return data;
}

export async function fetchComplaintHistory(id) {
  const { data } = await api.get(`/complaints/${id}/history`);
  return data;
}

export async function fetchDashboardStats() {
  const { data } = await api.get('/complaints/stats/dashboard');
  return data;
}

// ---- Inference ----

export async function detectOnly(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/inference/detect', form);
  return data;
}

export async function fetchInferenceStatus() {
  const { data } = await api.get('/inference/status');
  return data;
}

// ---- Geo ----

export async function reverseGeocode(latitude, longitude) {
  const { data } = await api.get('/geo/reverse', { params: { latitude, longitude } });
  return data;
}

// ---- Lifecycle ----

export async function fetchStatuses() {
  const { data } = await api.get('/lifecycle/statuses');
  return data;
}

export async function escalateComplaint(id) {
  const { data } = await api.post(`/lifecycle/escalate/${id}`);
  return data;
}

// ---- Health ----

export async function fetchHealth() {
  const { data } = await api.get('/health');
  return data;
}

export default api;
