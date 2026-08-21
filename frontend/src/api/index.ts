// MODULE 9.1 — All Axios API calls to the WorkPulse AI FastAPI backend.
import axios from "axios";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// ── Types (mirrors api/schemas.py) ──

export interface StatusComponent {
  connected: boolean;
  detail: string;
}

export interface SystemStatus {
  ollama: StatusComponent;
  agent: StatusComponent;
  database: StatusComponent;
  gmail: StatusComponent;
  playwright: StatusComponent;
}

export interface ProductivityScore {
  date: string;
  focus_score: number | null;
  productive_seconds: number;
  total_active_seconds: number;
  productive_hours_formatted: string;
  work_start: string | null;
  work_end: string | null;
  longest_focus_seconds: number;
}

export interface AppSummary {
  app_name: string;
  total_seconds: number;
  category: string;
  sessions: number;
}

export interface DarReport {
  id: number;
  date: string;
  content: string;
  productivity_score: number | null;
  total_active_seconds: number | null;
  productive_seconds: number | null;
  generated_at: string | null;
  emailed_at: string | null;
}

export type Category = "productive" | "neutral" | "distraction" | "uncategorised";

export interface ActivityLogEntry {
  id: number;
  app_name: string;
  window_title: string | null;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
  category: Category;
  date: string;
}

export interface IdlePeriod {
  id: number;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
  date: string;
}

export interface ContextSwitchingHour {
  hour: number;
  switch_count: number;
}

export interface ScreenshotEntry {
  id: number;
  file_path: string;
  thumbnail_path: string | null;
  original_path: string | null;
  timestamp: string;
  date: string;
  is_blurred: boolean;
  cloud_url: string | null;
}

// ── Calls ──

export const getStatus = () => api.get<SystemStatus>("/api/status").then((r) => r.data);

export const getTodayScore = () =>
  api.get<ProductivityScore>("/api/productivity/score/today").then((r) => r.data);

export const getScoreByDate = (date: string) =>
  api.get<ProductivityScore>(`/api/productivity/score/date/${date}`).then((r) => r.data);

export const getTodayAppsSummary = () =>
  api.get<AppSummary[]>("/api/activity/apps/summary").then((r) => r.data);

export const captureScreenshotNow = () =>
  api.post("/api/screenshots/capture").then((r) => r.data);

// DAR generation runs a full Ollama narrative pass (classification of any
// pending activity, then a multi-section report) — observed to take up to
// ~3 minutes on CPU inference. The default 15s client timeout would fail
// this long before the backend even has a chance to finish or time out.
export const generateDarNow = () =>
  api.post<DarReport>("/api/reports/dar/generate", null, { timeout: 300_000 }).then((r) => r.data);

export const getActivityByDate = (date: string) =>
  api.get<ActivityLogEntry[]>(`/api/activity/date/${date}`).then((r) => r.data);

export const getIdlePeriodsByDate = (date: string) =>
  api.get<IdlePeriod[]>(`/api/activity/idle/date/${date}`).then((r) => r.data);

export const getContextSwitchingByDate = (date: string) =>
  api.get<ContextSwitchingHour[]>("/api/activity/context-switching", { params: { target_date: date } }).then(
    (r) => r.data
  );

export const getScreenshotsByDate = (date: string) =>
  api.get<ScreenshotEntry[]>(`/api/screenshots/date/${date}`).then((r) => r.data);

export interface DailyScore {
  date: string;
  focus_score: number | null;
}

export interface FocusSession {
  start: string;
  end: string;
  duration_seconds: number;
  interrupted_by_distraction: boolean;
}

export interface FocusSessionsSummary {
  session_count: number;
  average_session_seconds: number;
  longest_session_seconds: number;
  interrupted_count: number;
  sessions: FocusSession[];
}

export interface HeatmapCell {
  date: string;
  hour: number;
  focus_score: number | null;
}

export const getDailyScores = (days = 7) =>
  api.get<DailyScore[]>("/api/productivity/daily-scores", { params: { days } }).then((r) => r.data);

export const getFocusSessionsToday = () =>
  api.get<FocusSessionsSummary>("/api/productivity/focus-sessions/today").then((r) => r.data);

export const getPeakHoursHeatmap = (days = 7) =>
  api.get<HeatmapCell[]>("/api/productivity/heatmap", { params: { days } }).then((r) => r.data);

export interface WeeklyReport {
  id: number;
  week_start: string;
  content: string;
  generated_at: string | null;
  emailed_at: string | null;
}

export const getAllDars = () => api.get<DarReport[]>("/api/reports/dar/all").then((r) => r.data);

export const getDarByDate = (date: string) =>
  api.get<DarReport>(`/api/reports/dar/date/${date}`).then((r) => r.data);

// Mirrors generateDarNow's long timeout — resend just emails already-
// generated content so it's fast, but keep this generous for consistency.
export const sendDarByDate = (date: string) =>
  api.post<DarReport>(`/api/reports/dar/date/${date}/send`, null, { timeout: 60_000 }).then((r) => r.data);

export const getLatestWeeklyReport = () =>
  api.get<WeeklyReport>("/api/reports/weekly/latest").then((r) => r.data);

export type AlertType = "focus" | "distraction" | "wellbeing" | "manager";

export interface Alert {
  id: number;
  alert_type: AlertType;
  message: string;
  triggered_at: string;
  dismissed_at: string | null;
  emailed: boolean;
}

export interface AlertPreference {
  enabled: boolean;
  threshold_value: number | null;
}

export const getAlerts = () => api.get<Alert[]>("/api/alerts").then((r) => r.data);

export const getUnreadAlertCount = () =>
  api.get<{ unread_count: number }>("/api/alerts/unread-count").then((r) => r.data.unread_count);

export const dismissAlert = (id: number) =>
  api.post<Alert>(`/api/alerts/${id}/dismiss`).then((r) => r.data);

export const getAlertPreferences = () =>
  api.get<Record<AlertType, AlertPreference>>("/api/alerts/preferences").then((r) => r.data);

export const updateAlertPreference = (alertType: AlertType, update: AlertPreference) =>
  api.put<AlertPreference>(`/api/alerts/preferences/${alertType}`, update).then((r) => r.data);
