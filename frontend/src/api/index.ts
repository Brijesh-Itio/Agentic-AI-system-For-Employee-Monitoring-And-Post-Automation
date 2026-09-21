// MODULE 9.1 — All Axios API calls to the WorkPulse AI FastAPI backend.
import axios from "axios";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// Login/logout + RBAC — attaches the bearer token to every request once
// AuthContext has one, and notifies AuthContext when a token is rejected
// (expired/invalid) so it can log the user out instead of every screen
// independently handling its own 401s.
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

let unauthorizedHandler: (() => void) | null = null;
export const onUnauthorized = (handler: () => void) => {
  unauthorizedHandler = handler;
};

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }
    return Promise.reject(error);
  }
);

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
  active_seconds_live: number;
  active_hours_formatted: string;
  idle_seconds: number;
  idle_formatted: string;
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

// ── Calls ──

export const getStatus = () => api.get<SystemStatus>("/api/status").then((r) => r.data);

export const getTodayScore = () =>
  api.get<ProductivityScore>("/api/productivity/score/today").then((r) => r.data);

export const getScoreByDate = (date: string) =>
  api.get<ProductivityScore>(`/api/productivity/score/date/${date}`).then((r) => r.data);

export const getTodayAppsSummary = () =>
  api.get<AppSummary[]>("/api/activity/apps/summary").then((r) => r.data);

export const getAppsSummaryByDate = (date: string) =>
  api.get<AppSummary[]>("/api/activity/apps/summary", { params: { target_date: date } }).then((r) => r.data);

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

export interface PeriodSummary {
  days_requested: number;
  days_tracked: number;
  avg_focus_score: number | null;
  avg_active_seconds: number;
  avg_productive_seconds: number;
  avg_active_hours_formatted: string;
  avg_productive_hours_formatted: string;
}

export const getPeriodSummary = (days = 7) =>
  api.get<PeriodSummary>("/api/productivity/summary", { params: { days } }).then((r) => r.data);

export interface WeeklyReport {
  id: number;
  week_start: string;
  content: string;
  generated_at: string | null;
  emailed_at: string | null;
}

export const getAllDars = () => api.get<DarReport[]>("/api/reports/dar/all").then((r) => r.data);

export const getMemberDars = (userId: string) =>
  api.get<DarReport[]>(`/api/reports/dar/member/${userId}/all`).then((r) => r.data);

export const getDarByDate = (date: string) =>
  api.get<DarReport>(`/api/reports/dar/date/${date}`).then((r) => r.data);

// Mirrors generateDarNow's long timeout — resend just emails already-
// generated content so it's fast, but keep this generous for consistency.
export const sendDarByDate = (date: string) =>
  api.post<DarReport>(`/api/reports/dar/date/${date}/send`, null, { timeout: 60_000 }).then((r) => r.data);

export const getLatestWeeklyReport = () =>
  api.get<WeeklyReport>("/api/reports/weekly/latest").then((r) => r.data);

export type AlertType = "focus" | "distraction" | "wellbeing" | "manager" | "late_arrival" | "holiday_announcement";

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

// ── Module 7 extension: department-custom DAR templates & structured entries ──

export type FieldType = "text" | "textarea" | "number" | "date" | "select" | "url";

export interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  options: string[] | null;
}

export interface Department {
  id: number;
  name: string;
  created_at: string | null;
}

export interface DarTemplate {
  department_id: number | null;
  fields: FieldDef[];
  updated_at: string | null;
}

export type DarStatus = "not_started" | "in_progress" | "blocked" | "completed";

export interface DarEntry {
  id: number;
  date: string;
  department_id: number | null;
  task: string;
  task_description: string | null;
  start_time: string | null;
  end_time: string | null;
  comment: string | null;
  remarks: string | null;
  link: string | null;
  custom_fields: Record<string, unknown>;
  source: "manual" | "ai_draft" | "ai_pipeline";
  project: string | null;
  status: DarStatus;
  progress: number;
  task_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DarEntryInput {
  date: string;
  department_id: number | null;
  task: string;
  task_description?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  comment?: string | null;
  remarks?: string | null;
  link?: string | null;
  custom_fields: Record<string, unknown>;
  project?: string | null;
  status?: DarStatus;
  progress?: number;
  task_id?: number | null;
}

export const getDepartments = () => api.get<Department[]>("/api/departments").then((r) => r.data);

export const createDepartment = (name: string) =>
  api.post<Department>("/api/departments", { name }).then((r) => r.data);

export const deleteDepartment = (id: number) => api.delete(`/api/departments/${id}`);

export const getDepartmentTemplate = (departmentId: number) =>
  api.get<DarTemplate>(`/api/departments/${departmentId}/template`).then((r) => r.data);

export const setDepartmentTemplate = (departmentId: number, fields: FieldDef[]) =>
  api.put<DarTemplate>(`/api/departments/${departmentId}/template`, { fields }).then((r) => r.data);

export const getEntriesByDate = (date: string) =>
  api.get<DarEntry[]>(`/api/reports/dar/date/${date}/entries`).then((r) => r.data);

export const createEntry = (payload: DarEntryInput) =>
  api.post<DarEntry>("/api/reports/dar/entries", payload).then((r) => r.data);

export const updateEntry = (id: number, payload: Partial<DarEntryInput>) =>
  api.patch<DarEntry>(`/api/reports/dar/entries/${id}`, payload).then((r) => r.data);

export const deleteEntry = (id: number) => api.delete(`/api/reports/dar/entries/${id}`);

// AI drafting runs a full Ollama pass over the day log — measured at
// ~275s on this CPU-only hardware normally, but a real attempt still timed
// out at 420s under heavy system load (many Chrome/VS Code windows open
// competing for CPU) — matches the server-side 600s budget in api/config.py.
export const draftEntries = (date: string, departmentId: number) =>
  api
    .post<DarEntry[]>("/api/reports/dar/entries/draft", { date, department_id: departmentId }, { timeout: 600_000 })
    .then((r) => r.data);

// A plain `<a href>` to this endpoint won't carry the Authorization header
// api's axios interceptor attaches (browsers don't send it on a bare
// navigation), so the export always 401s that way — this fetches the file
// through the authenticated `api` instance instead and triggers the save
// client-side, the same technique the plain-text DAR export already used.
export type DarExportFormat = "csv" | "docx" | "pdf" | "xlsx";

export const downloadDarExport = async (date: string, format: DarExportFormat) => {
  const response = await api.get(`/api/reports/dar/date/${date}/export`, {
    params: { format },
    responseType: "blob",
  });
  const url = URL.createObjectURL(new Blob([response.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `dar_${date}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
};

export const importDarCsv = (date: string, file: File, departmentId: number | null) => {
  const form = new FormData();
  form.append("file", file);
  const params = departmentId != null ? { department_id: departmentId } : {};
  return api
    .post<DarEntry[]>(`/api/reports/dar/date/${date}/import`, form, { params })
    .then((r) => r.data);
};

// ── Module 17: Command Mode ──

export interface JobLogEntry {
  at: string;
  message: string;
}

export interface Job {
  id: string;
  command: string;
  action: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  logs: JobLogEntry[];
  result: string | null;
  created_at: string | null;
  completed_at: string | null;
}

// Command actions call real Ollama/Playwright pipelines that can run for
// minutes — the job itself runs in the background on the server regardless
// of this client timeout, so a slow response here just means polling picks
// it up on the next status check rather than the command failing.
export const runCommand = (command: string) =>
  api.post<Job>("/api/command", { command }, { timeout: 20_000 }).then((r) => r.data);

export const getJobStatus = (jobId: string) => api.get<Job>(`/api/command/status/${jobId}`).then((r) => r.data);

export const getJobHistory = () => api.get<Job[]>("/api/command/history").then((r) => r.data);

export const cancelJob = (jobId: string) => api.post<Job>(`/api/command/cancel/${jobId}`).then((r) => r.data);

// ── Module 18: LinkedIn ──

export interface PostLogEntry {
  id: number;
  date: string;
  time: string;
  topic: string | null;
  content: string;
  post_id: string | null;
  platform: string;
  status: string;
  likes: number;
  comments: number;
  error: string | null;
}

export interface LinkedInStatus {
  can_post_now: boolean;
  last_post_at: string | null;
  minutes_until_next_allowed: number;
  posts_today: number;
  daily_limit: number;
}

export const getLinkedInPosts = () => api.get<PostLogEntry[]>("/api/linkedin/posts").then((r) => r.data);

export const getLinkedInStatus = () => api.get<LinkedInStatus>("/api/linkedin/status").then((r) => r.data);

// Kicks off the real pipeline (Ollama post writing -> Ollama image prompt +
// FastSD CPU image generation -> real Playwright posting, ~3-4 minutes
// total on CPU) as a background job and returns immediately — poll
// getJobStatus(job.id) (same job system as Command Mode) for live stage
// progress instead of waiting on one long request.
export const postToLinkedInNow = (topic?: string) =>
  api
    .post<Job>("/api/linkedin/post", null, { params: topic ? { topic } : {}, timeout: 20_000 })
    .then((r) => r.data);

// ── Module 19: Email Campaigns ──

export interface CampaignLogEntry {
  id: number;
  date: string;
  time: string;
  name: string | null;
  email: string;
  company: string | null;
  subject: string | null;
  status: string;
  error: string | null;
  follow_up_sent: boolean;
}

export interface CampaignStats {
  total_sent: number;
  total_failed: number;
  sent_today: number;
  daily_limit: number;
}

export interface CampaignRunResult {
  attempted: number;
  sent: number;
  skipped_unpersonalisable: number;
  failed: number;
}

export const getCampaignLog = () => api.get<CampaignLogEntry[]>("/api/email/campaigns").then((r) => r.data);

export const getCampaignStats = () => api.get<CampaignStats>("/api/email/campaigns/stats").then((r) => r.data);

// Real Ollama call per lead + real SMTP sends — can take a while for a
// larger batch.
export const runEmailCampaign = (limit?: number) =>
  api
    .post<CampaignRunResult>("/api/email/campaign/run", null, { params: limit ? { limit } : {}, timeout: 300_000 })
    .then((r) => r.data);

export const runFollowUps = () =>
  api.post<CampaignRunResult>("/api/email/follow-ups/run", null, { timeout: 300_000 }).then((r) => r.data);

export const testGmailConnection = () =>
  api.post<{ connected: boolean }>("/api/email/test-connection").then((r) => r.data);

// ── HR-customisable email templates (not one of the original modules) ──

export interface EmailTemplate {
  template_key: string;
  label: string;
  subject: string;
  body: string;
  variables: string;
  is_custom: boolean;
  updated_by: string | null;
  updated_at: string | null;
}

export const getEmailTemplates = () => api.get<EmailTemplate[]>("/api/email-templates").then((r) => r.data);

export const updateEmailTemplate = (key: string, subject: string, body: string) =>
  api.put<EmailTemplate>(`/api/email-templates/${key}`, { subject, body }).then((r) => r.data);

export const resetEmailTemplate = (key: string) =>
  api.post<EmailTemplate>(`/api/email-templates/${key}/reset`).then((r) => r.data);

export const previewEmailTemplate = (key: string, subject: string, body: string) =>
  api.post<{ subject: string; body: string }>(`/api/email-templates/${key}/preview`, { subject, body }).then((r) => r.data);

export const sendTestEmailTemplate = (key: string) =>
  api.post<{ sent: boolean; to: string }>(`/api/email-templates/${key}/send-test`).then((r) => r.data);

// ── Module 5 / 20: Leads ──

export interface LeadEntry {
  id: number;
  name: string;
  company: string | null;
  role: string | null;
  interest: string | null;
  email: string | null;
  notes: string | null;
  last_contact: string | null;
  source: string | null;
  status: string;
  created_at: string | null;
}

export interface LeadInput {
  name: string;
  company?: string | null;
  role?: string | null;
  interest?: string | null;
  email?: string | null;
  notes?: string | null;
  source?: string | null;
  status?: string;
}

export const getLeads = (status?: string) =>
  api.get<LeadEntry[]>("/api/leads", { params: status ? { status } : {} }).then((r) => r.data);

export const createLead = (payload: LeadInput) => api.post<LeadEntry>("/api/leads", payload).then((r) => r.data);

export const updateLead = (id: number, payload: Partial<LeadInput>) =>
  api.patch<LeadEntry>(`/api/leads/${id}`, payload).then((r) => r.data);

export const deleteLead = (id: number) => api.delete(`/api/leads/${id}`);

// Real Playwright sessions against Google/LinkedIn — can take a while, and
// commonly fails honestly (both sites block automated access; see
// DEVELOPMENT.md Module 20).
export const runLeadResearch = (targetProfile: string) =>
  api
    .post<{ status: string; detail: string; leads_found: number }>(
      "/api/leads/research", null, { params: { target_profile: targetProfile }, timeout: 120_000 }
    )
    .then((r) => r.data);

// ── Login & Role-Based Access (not one of the original 24 modules — added
// afterward so managers/admins can see what employees are doing) ──

export type Role = "employee" | "manager" | "admin" | "hr";
export const OVERSIGHT_ROLES: Role[] = ["manager", "admin"];
export const HR_ROLES: Role[] = ["hr", "admin"];

export interface TeamUser {
  id: string;
  name: string;
  email: string | null;
  role: Role;
  organisation_id: string | null;
  created_at: string | null;
  has_password: boolean;
}

export interface TeamUserInput {
  id: string;
  name: string;
  email?: string | null;
  role?: Role;
  organisation_id?: string | null;
  password?: string | null;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: TeamUser;
}

export const getBootstrapStatus = () =>
  api.get<{ needs_setup: boolean }>("/api/auth/bootstrap-status").then((r) => r.data);

export const login = (userId: string, password: string) =>
  api.post<AuthTokenResponse>("/api/auth/login", { user_id: userId, password }).then((r) => r.data);

export const getSsoStatus = () =>
  api.get<{ google_enabled: boolean }>("/api/auth/sso/status").then((r) => r.data);

// Full-page redirect, not an axios call — the browser needs to actually
// navigate to Google, not fetch this URL in the background.
export const googleSsoLoginUrl = () => `${API_BASE_URL}/api/auth/sso/google/login`;

export const logout = () => api.post("/api/auth/logout").then((r) => r.data);

export const getMe = () => api.get<TeamUser>("/api/auth/me").then((r) => r.data);

export const changePassword = (password: string) =>
  api.post("/api/auth/change-password", { password }).then((r) => r.data);

export const setUserPassword = (userId: string, password: string) =>
  api.post(`/api/team/users/${userId}/password`, { password }).then((r) => r.data);

export const updateUserRole = (userId: string, role: Role) =>
  api.patch<TeamUser>(`/api/team/users/${userId}/role`, { role }).then((r) => r.data);

export const updateUserProfile = (userId: string, payload: { name?: string; email?: string | null }) =>
  api.patch<TeamUser>(`/api/team/users/${userId}/profile`, payload).then((r) => r.data);

export const deleteTeamUser = (userId: string) => api.delete(`/api/team/users/${userId}`);

export type MemberStatus = "active" | "idle" | "offline";

export interface TeamMemberStatus {
  user: TeamUser;
  status: MemberStatus;
  focus_score: number | null;
  active_hours_today: number;
  current_app: string | null;
}

export interface MemberWeeklyStats {
  user_id: string;
  name: string;
  avg_focus_score: number | null;
  total_hours: number;
  productive_hours: number;
  avg_switch_count: number;
  days_with_data: number;
}

export interface BurnoutRisk {
  name: string;
  risk: string;
  reason: string;
}

export interface TeamAnalysis {
  members: MemberWeeklyStats[];
  high_performers: string[];
  struggling_members: string[];
  workload_imbalance: string;
  bottlenecks: string;
  rebalancing_suggestions: string[];
  burnout_risk: BurnoutRisk[];
  raw_summary: string | null;
}

export const getTeamUsers = () => api.get<TeamUser[]>("/api/team/users").then((r) => r.data);

export const createTeamUser = (payload: TeamUserInput) =>
  api.post<TeamUser>("/api/team/users", payload).then((r) => r.data);

export const getTeamOverview = () => api.get<TeamMemberStatus[]>("/api/team/overview").then((r) => r.data);

export const getMemberActivity = (userId: string, targetDate?: string) =>
  api
    .get<ActivityLogEntry[]>(`/api/team/member/${userId}/activity`, {
      params: targetDate ? { target_date: targetDate } : {},
    })
    .then((r) => r.data);

// Real Ollama call over the whole team's weekly data — same cost profile as
// other on-demand generation endpoints (matches api/config.py's
// OLLAMA_GENERATE_TIMEOUT_SECONDS=600; the old 120s client timeout was
// aborting the request client-side before the backend's own 600s budget
// was anywhere near up, surfacing as a false "Analysis failed" even though
// the call was still succeeding server-side — verified directly).
export const getTeamAnalysis = (windowDays = 7) =>
  api
    .get<TeamAnalysis>("/api/team/analysis", { params: { window_days: windowDays }, timeout: 600_000 })
    .then((r) => r.data);

// ── Attendance ──
// Entirely derived from daily_stats (itself built from real activity_logs
// tracking) — no manual clock-in/out exists anywhere in this app.

export type AttendanceStatus = "week_off" | "full_day" | "half_day" | "absent" | "upcoming";

// Mirrors agent/config.py's MONTHLY_LATE_WARNING_THRESHOLD — the count at
// which the backend fires the late-arrival warning alert + email.
export const MONTHLY_LATE_WARNING_THRESHOLD = 3;

export interface AttendanceDay {
  date: string;
  status: AttendanceStatus;
  week_off_reason: string | null;
  check_in: string | null;
  check_out: string | null;
  active_seconds: number;
  active_hours_formatted: string;
  focus_score: number | null;
  is_late: boolean;
  is_half_day_checkout: boolean;
}

export interface AttendanceSummary {
  month: string;
  full_days: number;
  half_days: number;
  absents: number;
  week_offs: number;
  late_count: number;
  days: AttendanceDay[];
}

export const getMyAttendance = (month: string) =>
  api.get<AttendanceSummary>("/api/attendance/me", { params: { month } }).then((r) => r.data);

export const getMemberAttendance = (userId: string, month: string) =>
  api.get<AttendanceSummary>(`/api/attendance/${userId}`, { params: { month } }).then((r) => r.data);

// ── Org-wide holiday calendar — HR/admin can declare, everyone can read ──

export type HolidayType = "holiday" | "paid_holiday";

export interface CompanyHoliday {
  id: number;
  date: string;
  title: string;
  holiday_type: HolidayType;
  description: string | null;
  created_by: string;
  created_at: string | null;
}

export interface CompanyHolidayCreate {
  date: string;
  title: string;
  holiday_type: HolidayType;
  description?: string | null;
}

export const getHolidays = (start?: string, end?: string) =>
  api.get<CompanyHoliday[]>("/api/holidays", { params: { start, end } }).then((r) => r.data);

export const createHoliday = (payload: CompanyHolidayCreate) =>
  api.post<CompanyHoliday>("/api/holidays", payload).then((r) => r.data);

export const deleteHoliday = (id: number) => api.delete(`/api/holidays/${id}`).then((r) => r.data);

// ── Feature flags — admin-controlled per-employee monitoring toggles ──
// Independent of AlertPreference above, which the employee sets for
// themselves; these are the admin's kill switches, enforced by the
// desktop agent itself (see agent/app_tracker.py etc.), not just hidden
// on the dashboard.

export type FeatureFlag = "activity_tracking" | "dar_generation" | "alerts_enabled";

export const FEATURE_FLAG_LABELS: Record<FeatureFlag, string> = {
  activity_tracking: "App & Website Tracking",
  dar_generation: "Automatic DAR Generation",
  alerts_enabled: "Alert Notifications",
};

export const getMemberFeatures = (userId: string) =>
  api.get<Record<FeatureFlag, boolean>>(`/api/team/member/${userId}/features`).then((r) => r.data);

export const setMemberFeature = (userId: string, feature: FeatureFlag, enabled: boolean) =>
  api
    .put<Record<FeatureFlag, boolean>>(`/api/team/member/${userId}/features/${feature}`, { enabled })
    .then((r) => r.data);

// ── SEO Agentic AI (modules 25-31) ──

export interface SeoSite {
  id: number;
  name: string;
  base_url: string;
  cms_type: string;
  cms_base_url: string | null;
  is_active: boolean;
  created_at: string | null;
  // NULL means "fall back to the GSC_SITE_URL/GA4_PROPERTY_ID in .env" —
  // see agent/database.py's _SEO_SITES_EXTRA_COLUMNS comment.
  gsc_site_url: string | null;
  ga4_property_id: string | null;
  // Same fallback story for CMS publishing credentials (module 34.2).
  // cms_username/cms_collection_id aren't secrets; cms_app_password/
  // cms_api_token never come back from the API once saved — only
  // whether one is set.
  cms_username: string | null;
  cms_collection_id: string | null;
  cms_app_password_set: boolean;
  cms_api_token_set: boolean;
  // Direct SFTP server access — host/port/username aren't secrets;
  // ssh_password never comes back from the API once saved.
  ssh_host: string | null;
  ssh_port: string | null;
  ssh_username: string | null;
  ssh_protocol: string | null;
  ssh_password_set: boolean;
}

export interface SshStatus {
  site_id: number;
  reachable: boolean;
  error: string | null;
}

export const getSeoSites = () => api.get<SeoSite[]>("/api/seo/sites").then((r) => r.data);

export const createSeoSite = (payload: {
  name: string;
  base_url: string;
  cms_type: "wordpress" | "webflow";
  gsc_site_url?: string;
  ga4_property_id?: string;
}) => api.post<SeoSite>("/api/seo/sites", payload).then((r) => r.data);

// Lets a site's Search Console/Analytics property be set from the UI
// instead of editing .env and restarting the backend for every site.
export const updateSeoSiteGoogleConfig = (
  siteId: number,
  payload: { gsc_site_url?: string; ga4_property_id?: string }
) => api.patch<SeoSite>(`/api/seo/sites/${siteId}/google-config`, payload).then((r) => r.data);

// Same idea for CMS publishing credentials — WordPress reads base_url/
// username/app_password, Webflow reads api_token/collection_id.
export const updateSeoSiteCmsConfig = (
  siteId: number,
  payload: {
    cms_base_url?: string;
    cms_username?: string;
    cms_app_password?: string;
    cms_api_token?: string;
    cms_collection_id?: string;
  }
) => api.patch<SeoSite>(`/api/seo/sites/${siteId}/cms-config`, payload).then((r) => r.data);

// Direct SFTP server access — for files a CMS REST API can't reach at all
// (wp-content/mu-plugins/*.php, .htaccess).
export const updateSeoSiteSshConfig = (
  siteId: number,
  payload: { ssh_host?: string; ssh_port?: string; ssh_username?: string; ssh_protocol?: string; ssh_password?: string }
) => api.patch<SeoSite>(`/api/seo/sites/${siteId}/ssh-config`, payload).then((r) => r.data);

export const getSshStatus = (siteId: number) =>
  api.get<SshStatus>(`/api/seo/sites/${siteId}/ssh-status`).then((r) => r.data);

export interface ServerDirEntry {
  name: string;
  is_dir: boolean;
  size: number | null;
}

export interface ServerDirListing {
  path: string;
  entries: ServerDirEntry[];
}

export interface ServerFileContent {
  path: string;
  content: string;
}

export const listServerDir = (siteId: number, path: string) =>
  api.get<ServerDirListing>("/api/seo/server/list", { params: { site_id: siteId, path } }).then((r) => r.data);

export const readServerFile = (siteId: number, path: string) =>
  api.get<ServerFileContent>("/api/seo/server/file", { params: { site_id: siteId, path } }).then((r) => r.data);

export const writeServerFile = (siteId: number, path: string, content: string) =>
  api.put<ServerFileContent>("/api/seo/server/file", { site_id: siteId, path, content }).then((r) => r.data);

export const renameServerFile = (siteId: number, path: string, newPath: string) =>
  api.post("/api/seo/server/rename", { site_id: siteId, path, new_path: newPath }).then((r) => r.data);

export const deleteServerFile = (siteId: number, path: string) =>
  api.delete("/api/seo/server/file", { params: { site_id: siteId, path } }).then((r) => r.data);

// Every write/rename/delete over Server Access automatically snapshots
// the file's prior content — see api/routes/seo.py's _backup_current_state.
export interface ServerFileBackupSummary {
  id: number;
  path: string;
  action: "write" | "rename" | "delete";
  new_path: string | null;
  created_at: string | null;
}

export interface ServerFileBackup extends ServerFileBackupSummary {
  content: string | null;
}

export const listServerFileBackups = (siteId: number, path: string, limit = 50) =>
  api
    .get<ServerFileBackupSummary[]>("/api/seo/server/backups", { params: { site_id: siteId, path, limit } })
    .then((r) => r.data);

export const getServerFileBackup = (backupId: number) =>
  api.get<ServerFileBackup>(`/api/seo/server/backups/${backupId}`).then((r) => r.data);

export const restoreServerFileBackup = (backupId: number) =>
  api.post<ServerFileContent>(`/api/seo/server/backups/${backupId}/restore`, {}).then((r) => r.data);

// Records a backup the moment editing actually starts (first real
// keystroke) — server-side, not a local download, so it lives in the
// same 15-day-retained history as every write/rename/delete backup.
export const createServerFileBackup = (siteId: number, path: string, content: string) =>
  api
    .post<ServerFileBackupSummary>("/api/seo/server/backups", { site_id: siteId, path, content })
    .then((r) => r.data);

// ── Job history + GSC/GA4 data — previously API-only, no UI ──
export interface SeoJobRun {
  id: number;
  site_id: number;
  job_type: string;
  run_date: string;
  status: "running" | "success" | "failed";
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export const getSeoJobs = (siteId: number, limit = 20) =>
  api.get<SeoJobRun[]>("/api/seo/jobs", { params: { site_id: siteId, limit } }).then((r) => r.data);

export interface GscQueryRow {
  id: number;
  site_id: number;
  run_date: string;
  query: string;
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
}

export const getGscQueries = (siteId: number, limit = 10) =>
  api.get<GscQueryRow[]>("/api/seo/gsc", { params: { site_id: siteId, limit } }).then((r) => r.data);

export interface Ga4PageRow {
  id: number;
  site_id: number;
  run_date: string;
  page_path: string;
  sessions: number;
  bounce_rate: number | null;
  conversions: number | null;
}

export const getGa4Pages = (siteId: number, limit = 10) =>
  api.get<Ga4PageRow[]>("/api/seo/ga4", { params: { site_id: siteId, limit } }).then((r) => r.data);

export interface GscPageRow {
  id: number;
  site_id: number;
  run_date: string;
  page: string;
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
}

export const getGscPages = (siteId: number, limit = 10) =>
  api.get<GscPageRow[]>("/api/seo/gsc/pages", { params: { site_id: siteId, limit } }).then((r) => r.data);

export const pullGscPages = (siteId: number, daysBack = 28) =>
  api
    .post<GscPageRow[]>("/api/seo/gsc/pages/pull", { site_id: siteId, days_back: daysBack })
    .then((r) => r.data);

export interface RankChange {
  query: string;
  previous_position: number;
  current_position: number;
  delta: number;
}

export const getRankAlerts = (siteId: number, onlyDrops = false) =>
  api
    .get<RankChange[]>("/api/seo/gsc/rank-alerts", { params: { site_id: siteId, only_drops: onlyDrops } })
    .then((r) => r.data);

export type MetaRewriteStatus = "queued" | "approved" | "rejected";

export interface MetaRewrite {
  id: number;
  site_id: number;
  url: string;
  run_date: string;
  impressions: number;
  clicks: number;
  ctr: number | null;
  position: number | null;
  suggested_title: string | null;
  suggested_description: string | null;
  status: MetaRewriteStatus;
  created_at: string | null;
  reviewed_at: string | null;
}

export const getMetaRewrites = (siteId: number, status?: string, limit = 50) =>
  api
    .get<MetaRewrite[]>("/api/seo/meta-rewrites", { params: { site_id: siteId, status, limit } })
    .then((r) => r.data);

export const approveMetaRewrite = (itemId: number) =>
  api.post<MetaRewrite>(`/api/seo/meta-rewrites/${itemId}/approve`, {}).then((r) => r.data);

export const rejectMetaRewrite = (itemId: number) =>
  api.post<MetaRewrite>(`/api/seo/meta-rewrites/${itemId}/reject`, {}).then((r) => r.data);

export type TechnicalIssueSeverity = "critical" | "warning" | "info";
export type TechnicalIssueStatus = "pending" | "approved" | "rejected" | "resolved";

// Rules where a real, ready-to-use replacement value is knowable AND this
// app has a real CMS write path for it (see ai/seo/issue_remediation.py's
// REMEDIABLE_RULES) — these get the one-click "Apply to website" button.
export const REMEDIABLE_RULES = ["duplicate_title", "missing_meta_description", "missing_canonical"];

// Rules with an exact, ready-to-paste fix value that's pure string/URL
// normalization (no LLM, no guessing) but no CMS field to write it to —
// see ai/seo/issue_remediation.py's DETERMINISTIC_FIX_RULES. Shown with
// the exact value but no "Apply to website" button; the human pastes it
// in themselves, then closes the issue out via "Mark as fixed".
export const DETERMINISTIC_FIX_RULES = ["url_structure", "unsafe_target_blank", "missing_meta_viewport", "missing_hsts"];

export interface TechnicalIssue {
  id: number;
  site_id: number;
  run_date: string;
  rule: string;
  severity: TechnicalIssueSeverity;
  url: string;
  message: string;
  suggested_fix: string;
  status: TechnicalIssueStatus;
  reviewed_at: string | null;
  reviewed_by: string | null;
  created_at: string | null;
  fix_value: string | null;
  fix_applied: boolean;
  fix_error: string | null;
  ai_suggestion: string | null;
}

export const getTechnicalIssues = (siteId: number, status?: string) =>
  api
    .get<TechnicalIssue[]>("/api/seo/technical/issues", { params: { site_id: siteId, status } })
    .then((r) => r.data);

// A real crawl+detect pass — can take real time (politeness delay per
// page) — long client timeout, same reasoning as reports.dar.generate.
export const runTechnicalAudit = (siteId: number, maxPages = 30) =>
  api
    .post<TechnicalIssue[]>(
      "/api/seo/technical/audit",
      { site_id: siteId, max_pages: maxPages },
      { timeout: 180_000 }
    )
    .then((r) => r.data);

export interface PageTagFinding {
  tag: string;
  detail: string;
  values: string[];
}

export interface PageTagAuditReport {
  url: string;
  missing_tags: PageTagFinding[];
  existing_tags: PageTagFinding[];
  duplicate_tags: PageTagFinding[];
  invalid_tags: PageTagFinding[];
}

// A single live fetch + classification, not a crawl — fast, but the
// target page's own server response time still applies, so a slightly
// longer-than-default timeout.
export const runPageTagAudit = (siteId: number, url: string) =>
  api
    .post<PageTagAuditReport>("/api/seo/technical/audit/page", { site_id: siteId, url }, { timeout: 30_000 })
    .then((r) => r.data);

export const approveTechnicalIssue = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/approve`, {}).then((r) => r.data);

export const rejectTechnicalIssue = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/reject`, {}).then((r) => r.data);

// Closes out an issue the human fixed themselves outside the app (most
// technical-audit rules have no safe automatic CMS write at all) — a
// pure status change, no live-site call.
export const resolveTechnicalIssue = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/resolve`, {}).then((r) => r.data);

export interface TechnicalIssueEditTarget {
  kind: "cms" | "static_file" | "unavailable";
  edit_url: string | null;
  file_path: string | null;
  detail: string;
}

// Resolves an issue's URL to somewhere to actually go fix it — a real
// WordPress edit screen for the CMS post behind it, or the exact file
// path on the server for a static page with no CMS post at all.
export const getTechnicalIssueEditTarget = (issueId: number) =>
  api.get<TechnicalIssueEditTarget>(`/api/seo/technical/issues/${issueId}/edit-target`, { timeout: 20_000 }).then((r) => r.data);

// Same resolution as above, but for an arbitrary URL (e.g. a specific
// .css/.js file PageSpeed's fix list points at) rather than a stored
// technical-issue row.
export const getUrlEditTarget = (siteId: number, url: string) =>
  api
    .get<TechnicalIssueEditTarget>("/api/seo/edit-target", { params: { site_id: siteId, url }, timeout: 20_000 })
    .then((r) => r.data);

// Read-only against the live page + one LLM call — no write happens here.
export const generateTechnicalIssueFix = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/generate-fix`, {}, { timeout: 30_000 }).then((r) => r.data);

// The one action that writes to the real site — requires the issue to
// already be approved and a fix generated first (the backend enforces
// both, this is just the call).
export const applyTechnicalIssueFix = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/apply-fix`, {}, { timeout: 30_000 }).then((r) => r.data);

// Advisory-only Ollama suggestion, available for EVERY rule (not just
// REMEDIABLE_RULES) — nothing writes this to the live site, unlike
// generate-fix/apply-fix above.
export const generateTechnicalIssueAiSuggestion = (issueId: number) =>
  api.post<TechnicalIssue>(`/api/seo/technical/issues/${issueId}/ai-suggestion`, {}, { timeout: 30_000 }).then((r) => r.data);

export interface SeoDigest {
  id: number;
  site_id: number;
  run_date: string;
  narrative: string;
  stats_json: string;
  slack_delivered: boolean;
  created_at: string | null;
  emailed_at: string | null;
}

export const getSeoDigests = (siteId: number) =>
  api.get<SeoDigest[]>("/api/seo/digest", { params: { site_id: siteId } }).then((r) => r.data);

// Module 58 — runDate backfills a specific past day's digest instead of
// always today's; sendEmail/emailRecipient reuse the same Gmail sender
// already live for DAR/alert email, so "export/share" isn't Slack + a
// Sheets tab only any more. Digest generation calls the LLM factory —
// generous timeout for local CPU inference, same reasoning as
// reports.dar.generate.
export const generateSeoDigest = (
  siteId: number,
  opts: { sendToSlack?: boolean; runDate?: string | null; sendEmail?: boolean; emailRecipient?: string | null } = {}
) =>
  api
    .post<SeoDigest>(
      "/api/seo/digest/generate",
      {
        site_id: siteId,
        send_to_slack: opts.sendToSlack ?? true,
        run_date: opts.runDate || undefined,
        send_email: opts.sendEmail ?? false,
        email_recipient: opts.emailRecipient || undefined,
      },
      { timeout: 120_000 }
    )
    .then((r) => r.data);

export type DigestRollupPeriod = "weekly" | "monthly" | "custom";

export interface DigestRollup {
  id: number;
  site_id: number;
  period: DigestRollupPeriod;
  period_start: string;
  period_end: string;
  narrative: string;
  stats_json: string;
  slack_delivered: boolean;
  created_at: string | null;
  emailed_at: string | null;
}

export const getDigestRollups = (siteId: number, period?: DigestRollupPeriod) =>
  api.get<DigestRollup[]>("/api/seo/digest/rollups", { params: { site_id: siteId, period } }).then((r) => r.data);

// Also runs on a schedule (Monday 07:30 weekly, 1st-of-month 07:45
// monthly) — this is the same on-demand trigger, useful for testing or
// forcing a fresh one without waiting. Module 58 — reference_date lets
// weekly/monthly pull a specific past week's/month's report instead of
// only ever the current one; period "custom" with start_date/end_date is
// a genuinely arbitrary range, not snapped to a week/month boundary at
// all. sendEmail/emailRecipient same as generateSeoDigest above.
export const generateDigestRollup = (
  siteId: number,
  period: DigestRollupPeriod,
  opts: {
    sendToSlack?: boolean;
    referenceDate?: string | null;
    startDate?: string | null;
    endDate?: string | null;
    sendEmail?: boolean;
    emailRecipient?: string | null;
  } = {}
) =>
  api
    .post<DigestRollup>(
      `/api/seo/digest/rollup/${period}`,
      {
        site_id: siteId,
        send_to_slack: opts.sendToSlack ?? true,
        reference_date: opts.referenceDate || undefined,
        start_date: opts.startDate || undefined,
        end_date: opts.endDate || undefined,
        send_email: opts.sendEmail ?? false,
        email_recipient: opts.emailRecipient || undefined,
      },
      { timeout: 120_000 }
    )
    .then((r) => r.data);

export interface SheetsStatus {
  configured: boolean;
  spreadsheet_id: string | null;
  url: string | null;
  error: string | null;
}

// Module 56 — three separate spreadsheets instead of one shared one:
// "main" (the automated daily pipeline's own logs), "gsc", and "ga4"
// (the two interactive "Export to Sheets" dashboards). kind defaults to
// "main" everywhere below so existing callers that never cared about
// the split keep working unchanged.
export type SheetsKind = "main" | "gsc" | "ga4" | "overview" | "social" | "blog";

// Creates the given kind's spreadsheet on first call (idempotent after
// that), sharing it with SEO_SHEETS_SHARE_EMAIL if set in .env.
// configured=false with an error is the honest result until the Sheets
// + Drive APIs are enabled for the Google Cloud project — see
// api/config.py's SEO_SHEETS_SHARE_EMAIL comment.
export const getSheetsStatus = (kind: SheetsKind = "main") =>
  api.get<SheetsStatus>("/api/seo/sheets", { params: { kind } }).then((r) => r.data);

export const shareSheets = (email: string, kind: SheetsKind = "main") =>
  api.post<SheetsStatus>("/api/seo/sheets/share", { email, kind }).then((r) => r.data);

// Service accounts created after April 2025 have zero Drive storage
// quota and can't create a new spreadsheet on their own (see api/routes
// /seo.py's adopt_sheets_route) — this is the real path: a human
// creates a normal Google Sheet in their own Drive, shares it with the
// service account as Editor, then hands the app that sheet's URL/id
// here. Accepts either a bare id or a full Google Sheets URL. Adopting
// all three kinds means calling this three times, once per kind.
export const adoptSheets = (spreadsheetIdOrUrl: string, kind: SheetsKind = "main") =>
  api
    .post<SheetsStatus>("/api/seo/sheets/adopt", { spreadsheet_id_or_url: spreadsheetIdOrUrl, kind })
    .then((r) => r.data);

export type SocialPlatform = "linkedin" | "twitter" | "instagram" | "facebook";
export type SocialPostStatus = "draft" | "approved" | "rejected" | "posted" | "failed";

export interface SocialPost {
  id: number;
  site_id: number;
  platform: SocialPlatform;
  source_url: string | null;
  content: string;
  // Required for Instagram to actually publish (its API has no
  // text-only post type) — optional for every other platform.
  image_url: string | null;
  status: SocialPostStatus;
  external_post_id: string | null;
  error: string | null;
  created_at: string | null;
  posted_at: string | null;
  // Which connected Facebook Page this posts through (module 40); null
  // means the single default account from .env. Ignored for every other
  // platform.
  facebook_account_id: number | null;
  // Module 41 — set means "auto-publish at this time once approved";
  // null means manual-publish-only.
  scheduled_for: string | null;
}

export const generateSocialPosts = (payload: {
  site_id: number;
  page_title: string;
  content_excerpt: string;
  source_url?: string;
  image_url?: string;
  platforms: SocialPlatform[];
  facebook_account_id?: number | null;
}) => api.post<SocialPost[]>("/api/seo/social/generate", payload, { timeout: 120_000 }).then((r) => r.data);

export const scheduleSocialPost = (postId: number, scheduledFor: string | null) =>
  api.post<SocialPost>(`/api/seo/social/${postId}/schedule`, { scheduled_for: scheduledFor }).then((r) => r.data);

export interface SocialBulkActionResult {
  post_id: number;
  ok: boolean;
  detail: string;
}

export const bulkApproveSocialPosts = (postIds: number[]) =>
  api.post<SocialBulkActionResult[]>("/api/seo/social/bulk-approve", { post_ids: postIds }).then((r) => r.data);

export const bulkPublishSocialPosts = (postIds: number[]) =>
  api
    .post<SocialBulkActionResult[]>("/api/seo/social/bulk-publish", { post_ids: postIds }, { timeout: 180_000 })
    .then((r) => r.data);

export const bulkGenerateSocialPosts = (payload: {
  site_id: number;
  topics: string[];
  platforms: SocialPlatform[];
  image_url?: string;
  facebook_account_id?: number | null;
}) => api.post<SocialPost[]>("/api/seo/social/bulk-generate", payload, { timeout: 0 }).then((r) => r.data);

export const generateSocialCalendar = (payload: {
  site_id: number;
  topics: string[];
  platforms: SocialPlatform[];
  start_date: string;
  days: number;
  post_time: string;
  image_url?: string;
  facebook_account_id?: number | null;
}) => api.post<SocialPost[]>("/api/seo/social/generate-calendar", payload, { timeout: 0 }).then((r) => r.data);

export interface SocialExportResult {
  ok: boolean;
  detail: string;
  sheet_url: string | null;
}

export const exportSocialPostsToSheet = (siteId: number) =>
  api.post<SocialExportResult>("/api/seo/social/export-to-sheet", { site_id: siteId }).then((r) => r.data);

export interface FacebookAccount {
  id: number;
  label: string;
  page_id: string;
  created_at: string | null;
}

export const getFacebookAccounts = () =>
  api.get<FacebookAccount[]>("/api/seo/facebook-accounts").then((r) => r.data);

export const createFacebookAccount = (payload: { label: string; page_id: string; page_access_token: string }) =>
  api.post<FacebookAccount>("/api/seo/facebook-accounts", payload).then((r) => r.data);

export const deleteFacebookAccount = (accountId: number) =>
  api.delete(`/api/seo/facebook-accounts/${accountId}`);

export const getSocialPosts = (siteId: number, status?: string) =>
  api.get<SocialPost[]>("/api/seo/social", { params: { site_id: siteId, status } }).then((r) => r.data);

export const updateSocialPost = (postId: number, content: string) =>
  api.patch<SocialPost>(`/api/seo/social/${postId}`, { content }).then((r) => r.data);

export const approveSocialPost = (postId: number) =>
  api.post<SocialPost>(`/api/seo/social/${postId}/approve`, {}).then((r) => r.data);

export const rejectSocialPost = (postId: number) =>
  api.post<SocialPost>(`/api/seo/social/${postId}/reject`, {}).then((r) => r.data);

export const publishSocialPost = (postId: number) =>
  api.post<SocialPost>(`/api/seo/social/${postId}/publish`, {}, { timeout: 60_000 }).then((r) => r.data);

export interface BacklinkMention {
  id: number;
  site_id: number;
  source_url: string;
  source_title: string | null;
  anchor_text: string | null;
  domain_rating: number | null;
  discovered_at: string | null;
  outreach_subject: string | null;
  outreach_body: string | null;
  created_at: string | null;
}

export const pullBacklinks = (siteId: number) =>
  api.post<BacklinkMention[]>("/api/seo/backlinks/pull", { site_id: siteId }, { timeout: 30_000 }).then((r) => r.data);

export const getBacklinks = (siteId: number) =>
  api.get<BacklinkMention[]>("/api/seo/backlinks", { params: { site_id: siteId } }).then((r) => r.data);

export const draftOutreachEmail = (mentionId: number, siteName: string, siteUrl: string) =>
  api
    .post<BacklinkMention>(
      `/api/seo/backlinks/${mentionId}/draft-outreach`,
      { site_name: siteName, site_url: siteUrl },
      { timeout: 60_000 }
    )
    .then((r) => r.data);

// Semrush domain-level metrics — Authority Score, organic/paid keywords,
// organic traffic, referring domains, backlinks count. NOT free: spends
// real purchased Semrush API units each time you check.
export interface SemrushMetrics {
  id: number;
  site_id: number;
  run_date: string;
  authority_score: number | null;
  organic_traffic: number | null;
  organic_keywords: number | null;
  paid_keywords: number | null;
  referring_domains: number | null;
  backlinks_total: number | null;
  semrush_rank: number | null;
  created_at: string | null;
}

export const checkSemrushMetrics = (siteId: number) =>
  api.post<SemrushMetrics>("/api/seo/semrush/check", { site_id: siteId }, { timeout: 30_000 }).then((r) => r.data);

export const getSemrushMetrics = (siteId: number, limit = 30) =>
  api.get<SemrushMetrics[]>("/api/seo/semrush", { params: { site_id: siteId, limit } }).then((r) => r.data);

export interface SemrushBacklinkRow {
  source_url: string;
  target_url: string;
  anchor: string;
  nofollow: boolean;
  first_seen: string;
  last_seen: string;
  page_authority_score: number | null;
}

export interface SemrushReferringDomainRow {
  domain: string;
  authority_score: number | null;
  backlinks_num: number | null;
  country: string;
  first_seen: string;
  last_seen: string;
}

export interface SemrushGapRow {
  target: string;
  authority_score: number | null;
  backlinks_num: number | null;
  referring_domains_num: number | null;
}

export const getSemrushBacklinks = (siteId: number, limit = 50) =>
  api
    .get<SemrushBacklinkRow[]>("/api/seo/semrush/backlinks", { params: { site_id: siteId, limit }, timeout: 30_000 })
    .then((r) => r.data);

export const getSemrushReferringDomains = (siteId: number, limit = 50) =>
  api
    .get<SemrushReferringDomainRow[]>("/api/seo/semrush/referring-domains", {
      params: { site_id: siteId, limit },
      timeout: 30_000,
    })
    .then((r) => r.data);

export const getSemrushBacklinkGap = (siteId: number, competitorDomains: string[]) =>
  api
    .post<SemrushGapRow[]>(
      "/api/seo/semrush/backlink-gap",
      { site_id: siteId, competitor_domains: competitorDomains },
      { timeout: 30_000 }
    )
    .then((r) => r.data);

// Module 37 — a third-party RapidAPI keyword wrapper (NOT Semrush's own
// official API — see automation/seo/rapidapi_keyword_client.py). Every
// live test this session returned the provider's own generic error
// shape rather than real data, so this returns the raw response as-is
// (unknown/unverified shape) rather than a typed model.
export const checkRapidApiKeywords = (siteId: number, country = "us") =>
  api
    .post<Record<string, unknown>>("/api/seo/keywords/rapidapi-check", { site_id: siteId, country }, { timeout: 90_000 })
    .then((r) => r.data);

// A DIFFERENT RapidAPI product ("Semrush Magic Tool", not the one
// above) — verified live returning real data: search volume, CPC,
// competition, intent, and 12-month trends for hundreds of related
// keywords from one seed keyword.
export interface MonthlySearches {
  month: string;
  year: number;
  searches: number;
}

export interface KeywordResearchRow {
  keyword: string;
  avg_monthly_searches: number | null;
  low_cpc: string | null;
  high_cpc: string | null;
  competition_index: number | null;
  competition_value: string | null;
  intent: string[];
  intent_confidence: number | null;
  advice: string[];
  content_gap_score: number | null;
  estimated_ctr: number | null;
  keyword_freshness: number | null;
  serp_feature_type: string | null;
  monetization_score: number | null;
  monthly_search_volumes: MonthlySearches[];
}

export const researchKeywords = (keyword: string, language = "en", country = "us") =>
  api
    .post<KeywordResearchRow[]>("/api/seo/keywords/research", { keyword, language, country }, { timeout: 90_000 })
    .then((r) => r.data);

// A THIRD distinct RapidAPI product/host (semrush-seo10), same
// application/key as researchKeywords above — verified live returning
// real difficulty score, volume, competition, CPC, and monthly trend.
export interface KeywordDifficulty {
  keyword: string;
  keyword_difficulty: number | null;
  volume: number | null;
  competition: number | null;
  cpc_dollars: number | null;
  monthly_volumes: Record<string, number>;
  search_intent: number[] | null;
}

export const checkKeywordDifficulty = (keyword: string, country = "us") =>
  api.post<KeywordDifficulty>("/api/seo/keywords/difficulty", { keyword, country }, { timeout: 30_000 }).then((r) => r.data);

// ── Module 47 — RapidAPI "SEMrush SEO" domain-analysis wrapper
// (semrush-seo3.p.rapidapi.com). Live-verified this session; Competitor
// Analysis on this same host is deliberately not included here — every
// live test returned the provider's own "Missing or invalid session
// credential" 401, a server-side bug on their end, not a request-shape
// problem this app could work around. ──

export interface BacklinkRow {
  url_from: string;
  url_to: string;
  title: string;
  anchor: string;
  nofollow: boolean;
  inlink_rank: number | null;
  domain_inlink_rank: number | null;
  first_seen: string;
  last_visited: string;
  date_lost: string;
  spam_score: number | null;
}

export const getTopBacklinks = (siteId: number, website: string) =>
  api.post<BacklinkRow[]>("/api/seo/backlinks/top", { site_id: siteId, website }, { timeout: 45_000 }).then((r) => r.data);

export interface DomainAuthority {
  domain: string;
  da: number | null;
  pa: number | null;
  spam_score: number | null;
  dr: number | null;
  org_traffic: number | null;
}

export const getDomainAuthority = (siteId: number, website: string) =>
  api
    .post<DomainAuthority>("/api/seo/backlinks/domain-authority", { site_id: siteId, website }, { timeout: 45_000 })
    .then((r) => r.data);

export const getBulkDomainAuthority = (siteId: number, domains: string[]) =>
  api
    .post<DomainAuthority[]>("/api/seo/backlinks/domain-authority/bulk", { site_id: siteId, domains }, { timeout: 45_000 })
    .then((r) => r.data);

export interface KeywordInsight {
  keyword: string;
  volume: number | null;
  competition: number | null;
  cpc_dollars: number | null;
  sd: number | null;
  monthly_volumes: Record<string, number>;
  search_intent: number[] | null;
}

export const getKeywordInsights = (keyword: string, country = "us") =>
  api.post<KeywordInsight>("/api/seo/keywords/insights", { keyword, country }, { timeout: 30_000 }).then((r) => r.data);

export interface SampleKeyword {
  keyword: string;
  position: number | null;
  search_volume: number | null;
  etv: number | null;
  cpc: number | null;
  url: string;
}

export interface WebsiteTraffic {
  domain: string;
  organic_etv: number | null;
  organic_keywords: number | null;
  ranked_keywords_total: number | null;
  estimated_paid_traffic_cost: number | null;
  position_distribution: Record<string, number>;
  sample_keywords: SampleKeyword[];
}

export const getWebsiteTraffic = (siteId: number, website: string) =>
  api
    .post<WebsiteTraffic>("/api/seo/backlinks/website-traffic", { site_id: siteId, website }, { timeout: 45_000 })
    .then((r) => r.data);

// semrush-seo3's /competitor.php — returned a provider-side 401 for every
// domain when first tested; the provider fixed it and it was re-verified
// live. bounce_rate is already a percentage (30.7 = 30.7%), time_on_site is
// seconds, and share/traffic_sources values are 0-1 fractions.
export interface CompetitorAnalysis {
  domain: string;
  title: string;
  description: string;
  global_rank: number | null;
  country_rank: number | null;
  registration_time: string;
  expiration_time: string;
  snapshot_date: string;
  engagement: {
    total_visits: number | null;
    time_on_site: number | null;
    pages_per_visit: number | null;
    bounce_rate: number | null;
  };
  monthly_visits: Record<string, number>;
  traffic_sources: Record<string, number>;
  top_countries: { country_code: string; share: number | null }[];
  top_keywords: { keyword: string; search_volume: number | null; estimated_value: number | null; cpc: number | null }[];
}

export const getCompetitorAnalysis = (siteId: number, website: string) =>
  api
    .post<CompetitorAnalysis>("/api/seo/backlinks/competitor-analysis", { site_id: siteId, website }, { timeout: 60_000 })
    .then((r) => r.data);

// ── Module 32 — PageSpeed resource audit + Indexing Status ──

export type PageSpeedStrategy = "mobile" | "desktop";

export interface PageSpeedResult {
  id: number;
  site_id: number;
  url: string;
  strategy: PageSpeedStrategy;
  run_date: string;
  performance_score: number | null;
  lcp_ms: number | null;
  cls: number | null;
  inp_ms: number | null;
  ttfb_ms: number | null;
  fcp_ms: number | null;
  created_at: string | null;
}

// A real Lighthouse run on Google's end — 20-40s is normal, but a slow/
// heavy page can push the backend through all 3 of its own 90s retry
// attempts before giving up, so this client timeout must clear that.
export const checkPageSpeed = (siteId: number, url: string, strategy: PageSpeedStrategy = "mobile") =>
  api
    .post<PageSpeedResult>("/api/seo/pagespeed/check", { site_id: siteId, url, strategy }, { timeout: 300_000 })
    .then((r) => r.data);

export const getPageSpeedResults = (siteId: number, limit?: number) =>
  api.get<PageSpeedResult[]>("/api/seo/pagespeed", { params: { site_id: siteId, limit } }).then((r) => r.data);

export interface PageSpeedOpportunityItem {
  url: string | null;
  wasted_bytes: number | null;
  wasted_ms: number | null;
  total_bytes: number | null;
}

export interface PageSpeedOpportunity {
  audit_id: string;
  title: string;
  description: string;
  savings_ms: number | null;
  savings_bytes: number | null;
  items: PageSpeedOpportunityItem[];
}

export interface ResourceAuditReport {
  total_requests: number | null;
  total_byte_weight_kb: number | null;
  unused_css_kb: number | null;
  unused_js_kb: number | null;
  render_blocking_requests: number | null;
  opportunities: PageSpeedOpportunity[];
}

// Parses raw_json already stored by checkPageSpeed above — no second
// PageSpeed API call, so this is fast even though the check itself isn't.
export const getPageSpeedOpportunities = (resultId: number) =>
  api.get<ResourceAuditReport>(`/api/seo/pagespeed/${resultId}/opportunities`).then((r) => r.data);

export interface IndexStatus {
  id: number;
  site_id: number;
  url: string;
  coverage_state: string | null;
  indexing_state: string | null;
  robots_txt_state: string | null;
  page_fetch_state: string | null;
  last_crawl_time: string | null;
  google_canonical: string | null;
  user_canonical: string | null;
  mobile_usability_verdict: string | null;
  inspection_result_link: string | null;
  crawled_as: string | null;
  sitemap_json: string | null;
  checked_at: string | null;
}

// The backend retries this up to 3 times with its own hard 40s deadline
// per attempt (see indexing_client.py) — this must clear that worst case.
export const inspectUrl = (siteId: number, url: string) =>
  api.post<IndexStatus>("/api/seo/indexing/inspect", { site_id: siteId, url }, { timeout: 150_000 }).then((r) => r.data);

export const getIndexStatusList = (siteId: number) =>
  api.get<IndexStatus[]>("/api/seo/indexing/status", { params: { site_id: siteId } }).then((r) => r.data);

export type IndexingNotificationType = "URL_UPDATED" | "URL_DELETED";

export interface IndexingSubmission {
  id: number;
  site_id: number;
  url: string;
  notification_type: IndexingNotificationType;
  success: boolean;
  error: string | null;
  submitted_at: string | null;
}

export const submitForIndexing = (siteId: number, url: string, notificationType: IndexingNotificationType = "URL_UPDATED") =>
  api
    .post<IndexingSubmission>(
      "/api/seo/indexing/submit",
      { site_id: siteId, url, notification_type: notificationType },
      { timeout: 30_000 }
    )
    .then((r) => r.data);

// ── Module 48/49 — GSC dimension filtering, Sitemaps management, Site
// Verification. Stateless — re-fetched live each time, no local table. ──

export interface GscDimensionRow {
  key: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface GscLiveQueryRow {
  query: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface GscLivePageRow {
  page: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface GscDateRow {
  date: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

// country: an ISO 3166-1 alpha-3 code, page: an exact page URL — the
// real Search Console UI's own "click a row to drill into it" filters,
// applied the same way here (and combinable, matching its filter-chip
// behavior). startDate/endDate (YYYY-MM-DD) override daysBack when both
// are given — the "Custom" date-range option.
export interface GscFilterParams {
  daysBack?: number;
  country?: string | null;
  page?: string | null;
  startDate?: string | null;
  endDate?: string | null;
  rowLimit?: number;
}

const fetchGscDimension = <T>(path: string, siteId: number, filters: GscFilterParams) =>
  api
    .post<T[]>(
      path,
      {
        site_id: siteId,
        days_back: filters.daysBack ?? 28,
        row_limit: filters.rowLimit,
        country: filters.country || undefined,
        page: filters.page || undefined,
        start_date: filters.startDate || undefined,
        end_date: filters.endDate || undefined,
      },
      { timeout: 30_000 }
    )
    .then((r) => r.data);

export const getGscQueriesLive = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscLiveQueryRow>("/api/seo/gsc/queries/live", siteId, filters);
export const getGscPagesLive = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscLivePageRow>("/api/seo/gsc/pages/live", siteId, filters);
export const getGscByCountry = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscDimensionRow>("/api/seo/gsc/country", siteId, filters);
export const getGscByDevice = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscDimensionRow>("/api/seo/gsc/device", siteId, filters);
export const getGscBySearchAppearance = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscDimensionRow>("/api/seo/gsc/search-appearance", siteId, filters);
export const getGscTimeseries = (siteId: number, filters: GscFilterParams = {}) =>
  fetchGscDimension<GscDateRow>("/api/seo/gsc/timeseries", siteId, { rowLimit: 1000, ...filters });

export interface GscExportRow {
  label: string;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface GscExportResult {
  ok: boolean;
  detail: string;
  sheet_url: string | null;
}

export const exportGscToSheet = (siteId: number, view: string, dateRange: string, rows: GscExportRow[]) =>
  api
    .post<GscExportResult>(
      "/api/seo/gsc/export-to-sheet",
      { site_id: siteId, view, date_range: dateRange, rows },
      { timeout: 30_000 }
    )
    .then((r) => r.data);

// Module 50 follow-up — exports every GSC dimension (Queries/Pages/
// Countries/Devices/Search Appearance) in one call, each landing in its
// own clean tab (matching the real Search Console UI's own per-dimension
// tables), instead of only whichever single view is on screen.
export interface GscExportAllData {
  queries?: GscExportRow[];
  pages?: GscExportRow[];
  countries?: GscExportRow[];
  devices?: GscExportRow[];
  search_appearance?: GscExportRow[];
  // Per-day clicks/impressions — the same data behind the in-app trend
  // chart — used to (re)embed a real chart on its own "GSC Chart" tab,
  // matching the real Search Console UI's own "Export > Google Sheets"
  // layout (a Chart tab ahead of the per-dimension tabs).
  timeseries?: GscDateRow[];
}

export const exportAllGscToSheet = (siteId: number, dateRange: string, focusView: string, data: GscExportAllData) =>
  api
    .post<GscExportResult>(
      "/api/seo/gsc/export-all-to-sheet",
      { site_id: siteId, date_range: dateRange, focus_view: focusView, ...data },
      { timeout: 45_000 }
    )
    .then((r) => r.data);

// ── Module 51 — GA4 dimension/timeseries live views and Sheets export,
// mirroring the GSC block immediately above. No country/page filter
// here — GA4's dimension pulls don't support combining filters the way
// GSC's do. ──

export interface Ga4DimensionRow {
  key: string;
  sessions: number;
  bounce_rate: number;
  conversions: number;
  active_users: number;
  new_users: number;
  total_users: number;
  event_count: number;
  engagement_rate: number;
  engaged_sessions: number;
  avg_session_duration: number;
}

export interface Ga4LivePageRow {
  page_path: string;
  sessions: number;
  bounce_rate: number;
  conversions: number;
  active_users: number;
  new_users: number;
  total_users: number;
  event_count: number;
  engagement_rate: number;
  engaged_sessions: number;
  avg_session_duration: number;
}

export interface Ga4DateRow {
  date: string;
  sessions: number;
  bounce_rate: number;
  conversions: number;
  active_users: number;
  new_users: number;
  total_users: number;
  event_count: number;
  engagement_rate: number;
  engaged_sessions: number;
  avg_session_duration: number;
}

export interface Ga4FilterParams {
  daysBack?: number;
  startDate?: string | null;
  endDate?: string | null;
  rowLimit?: number;
}

const fetchGa4Dimension = <T>(path: string, siteId: number, filters: Ga4FilterParams) =>
  api
    .post<T[]>(
      path,
      {
        site_id: siteId,
        days_back: filters.daysBack ?? 28,
        row_limit: filters.rowLimit,
        start_date: filters.startDate || undefined,
        end_date: filters.endDate || undefined,
      },
      { timeout: 30_000 }
    )
    .then((r) => r.data);

export const getGa4PagesLive = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4LivePageRow>("/api/seo/ga4/pages/live", siteId, filters);
export const getGa4BySource = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4DimensionRow>("/api/seo/ga4/sources/live", siteId, filters);
export const getGa4ByCountry = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4DimensionRow>("/api/seo/ga4/countries/live", siteId, filters);
export const getGa4ByDevice = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4DimensionRow>("/api/seo/ga4/devices/live", siteId, filters);
export const getGa4Timeseries = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4DateRow>("/api/seo/ga4/timeseries", siteId, { rowLimit: 1000, ...filters });

// Module 55 — GA4's own "Events: Event name" report.
export interface Ga4EventRow {
  event_name: string;
  event_count: number;
  total_users: number;
  active_users: number;
  total_revenue: number;
  event_count_per_active_user: number;
}

export const getGa4Events = (siteId: number, filters: Ga4FilterParams = {}) =>
  fetchGa4Dimension<Ga4EventRow>("/api/seo/ga4/events", siteId, { rowLimit: 100, ...filters });

export interface Ga4ExportRow {
  label: string;
  sessions: number;
  bounce_rate: number;
  conversions: number;
}

export interface Ga4ExportResult {
  ok: boolean;
  detail: string;
  sheet_url: string | null;
}

export interface Ga4EventExportRow {
  event_name: string;
  event_count: number;
  total_users: number;
  event_count_per_active_user: number;
  total_revenue: number;
}

export interface Ga4ExportAllData {
  pages?: Ga4ExportRow[];
  sources?: Ga4ExportRow[];
  countries?: Ga4ExportRow[];
  devices?: Ga4ExportRow[];
  events?: Ga4EventExportRow[];
  timeseries?: Ga4DateRow[];
}

export const exportAllGa4ToSheet = (siteId: number, dateRange: string, focusView: string, data: Ga4ExportAllData) =>
  api
    .post<Ga4ExportResult>(
      "/api/seo/ga4/export-all-to-sheet",
      { site_id: siteId, date_range: dateRange, focus_view: focusView, ...data },
      { timeout: 45_000 }
    )
    .then((r) => r.data);

// Module 57 — the site Overview dashboard's own "download this report"
// button (Top Search Queries / Top Traffic Pages / CTR by Page / Rank
// Alerts). Sends whatever's already on screen — each field reuses the
// same row shape its panel's own query already returns.
export interface OverviewExportData {
  top_queries?: GscQueryRow[];
  top_pages?: Ga4PageRow[];
  ctr_by_page?: GscPageRow[];
  rank_alerts?: RankChange[];
}

export interface OverviewExportResult {
  ok: boolean;
  detail: string;
  sheet_url: string | null;
}

export const exportOverviewToSheet = (siteId: number, data: OverviewExportData) =>
  api
    .post<OverviewExportResult>("/api/seo/overview/export-to-sheet", { site_id: siteId, ...data }, { timeout: 45_000 })
    .then((r) => r.data);

// Module 52 — active users right now, by country, matching GA4's own
// Home/Realtime report. No date range — GA4 itself defines "realtime"
// as the trailing ~30-minute window.
export interface Ga4RealtimeRow {
  country: string;
  active_users: number;
}

export const getGa4Realtime = (siteId: number) =>
  api.get<Ga4RealtimeRow[]>("/api/seo/ga4/realtime", { params: { site_id: siteId }, timeout: 15_000 }).then((r) => r.data);

// The fuller "Realtime overview" report — active users per minute, plus
// by device/page/audience, matching GA4's own dedicated Realtime page.
export interface Ga4RealtimeMinuteRow {
  minutes_ago: number;
  active_users: number;
}

export interface Ga4RealtimeDimensionRow {
  key: string;
  value: number;
}

export const getGa4RealtimeByMinute = (siteId: number) =>
  api.get<Ga4RealtimeMinuteRow[]>("/api/seo/ga4/realtime/by-minute", { params: { site_id: siteId }, timeout: 15_000 }).then((r) => r.data);
export const getGa4RealtimeByDevice = (siteId: number) =>
  api.get<Ga4RealtimeDimensionRow[]>("/api/seo/ga4/realtime/by-device", { params: { site_id: siteId }, timeout: 15_000 }).then((r) => r.data);
export const getGa4RealtimeByPage = (siteId: number) =>
  api.get<Ga4RealtimeDimensionRow[]>("/api/seo/ga4/realtime/by-page", { params: { site_id: siteId }, timeout: 15_000 }).then((r) => r.data);
export const getGa4RealtimeByAudience = (siteId: number) =>
  api.get<Ga4RealtimeDimensionRow[]>("/api/seo/ga4/realtime/by-audience", { params: { site_id: siteId }, timeout: 15_000 }).then((r) => r.data);

export interface SitemapContentType {
  type: string;
  submitted: number | null;
  indexed: number | null;
}

export interface SitemapInfo {
  path: string;
  last_submitted: string | null;
  is_pending: boolean | null;
  is_sitemaps_index: boolean | null;
  type: string | null;
  last_downloaded: string | null;
  warnings: number | null;
  errors: number | null;
  contents: SitemapContentType[];
}

export const getSitemaps = (siteId: number) =>
  api.post<SitemapInfo[]>("/api/seo/sitemaps", { site_id: siteId }, { timeout: 30_000 }).then((r) => r.data);

export interface SitemapActionResult {
  ok: boolean;
  detail: string;
}

export const submitSitemap = (siteId: number, feedpath: string) =>
  api
    .post<SitemapActionResult>("/api/seo/sitemaps/submit", { site_id: siteId, feedpath }, { timeout: 30_000 })
    .then((r) => r.data);

export const deleteSitemap = (siteId: number, feedpath: string) =>
  api
    .post<SitemapActionResult>("/api/seo/sitemaps/delete", { site_id: siteId, feedpath }, { timeout: 30_000 })
    .then((r) => r.data);

export interface VerifiedSite {
  id: string;
  type: string | null;
  identifier: string | null;
  owners: string[];
}

export const getVerifiedSites = () =>
  api.get<VerifiedSite[]>("/api/seo/site-verification", { timeout: 30_000 }).then((r) => r.data);

export const getIndexingSubmissions = (siteId: number) =>
  api.get<IndexingSubmission[]>("/api/seo/indexing/submissions", { params: { site_id: siteId } }).then((r) => r.data);

// ── Module 34: Blog post generation + CMS draft publishing ──
export type BlogPostStatus = "draft" | "approved" | "rejected" | "published" | "live" | "failed";

export interface StructureIssue {
  rule: string;
  severity: "error" | "warning";
  message: string;
}

export interface BlogPost {
  id: number;
  site_id: number;
  topic: string;
  primary_keyword: string | null;
  title: string;
  excerpt: string | null;
  content: string;
  structure_passed: boolean | null;
  structure_issues_json: string | null;
  status: BlogPostStatus;
  image_url: string | null;
  slug: string | null;
  // JSON-encoded arrays of plain names — JSON.parse before use, same
  // convention as structure_issues_json above.
  tags: string | null;
  categories: string | null;
  cms_post_id: string | null;
  cms_post_link: string | null;
  error: string | null;
  created_at: string | null;
  published_at: string | null;
  scheduled_at: string | null;
}

// A real, full-length post via the slower/better model (module 25's
// fast=False path) — genuinely takes over a minute, not the 20-40s a
// short social caption needs.
export const generateBlogPost = (payload: { site_id: number; topic: string; primary_keyword?: string; min_words?: number }) =>
  api.post<BlogPost>("/api/seo/blog/generate", payload, { timeout: 180_000 }).then((r) => r.data);

export const getBlogPosts = (siteId: number, status?: string) =>
  api.get<BlogPost[]>("/api/seo/blog", { params: { site_id: siteId, status } }).then((r) => r.data);

// Only works while status is still 'draft' — re-runs the structure
// checker server-side so the returned post's issue badges reflect the edit.
export const updateBlogPost = (postId: number, payload: { title: string; excerpt?: string; content: string }) =>
  api.patch<BlogPost>(`/api/seo/blog/${postId}`, payload).then((r) => r.data);

// Only while status is still 'draft' — these become the actual
// WordPress slug/tags/categories the moment Publish creates the post.
export const updateBlogPostTaxonomy = (postId: number, payload: { slug?: string; tags?: string[]; categories?: string[] }) =>
  api.patch<BlogPost>(`/api/seo/blog/${postId}/taxonomy`, payload).then((r) => r.data);

export const approveBlogPost = (postId: number) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/approve`, {}).then((r) => r.data);

export const rejectBlogPost = (postId: number) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/reject`, {}).then((r) => r.data);

// Creates the post as a draft in WordPress/Webflow — never goes live on
// its own, see automation/seo/cms/base.py's create_post docstring.
export const publishBlogPost = (postId: number) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/publish`, {}, { timeout: 30_000 }).then((r) => r.data);

// The explicit, separate "actually make it public" step — Publish only
// ever creates a CMS draft (see publishBlogPost's own comment above);
// this is what a human clicking "Go Live" triggers instead of having to
// open WordPress/Webflow's own admin to hit Publish there.
export const goLiveBlogPost = (postId: number) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/go-live`, {}, { timeout: 30_000 }).then((r) => r.data);

// Module 59 — bulk generation, content-calendar generation, scheduling,
// and bulk approve/publish for blog posts, mirroring the equivalent
// social-post functions (module 41) directly above.
export const scheduleBlogPost = (postId: number, scheduledAt: string | null) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/schedule`, { scheduled_at: scheduledAt }).then((r) => r.data);

export interface BlogBulkActionResult {
  post_id: number;
  ok: boolean;
  detail: string;
}

export const bulkApproveBlogPosts = (postIds: number[]) =>
  api.post<BlogBulkActionResult[]>("/api/seo/blog/bulk-approve", { post_ids: postIds }).then((r) => r.data);

export const bulkPublishBlogPosts = (postIds: number[]) =>
  api
    .post<BlogBulkActionResult[]>("/api/seo/blog/bulk-publish", { post_ids: postIds }, { timeout: 0 })
    .then((r) => r.data);

export const bulkGenerateBlogPosts = (payload: {
  site_id: number;
  topics: string[];
  min_words?: number;
  generate_image?: boolean;
}) => api.post<BlogPost[]>("/api/seo/blog/bulk-generate", payload, { timeout: 0 }).then((r) => r.data);

export const generateBlogCalendar = (payload: {
  site_id: number;
  topics: string[];
  start_date: string;
  days: number;
  post_time: string;
  min_words?: number;
  generate_image?: boolean;
}) => api.post<BlogPost[]>("/api/seo/blog/generate-calendar", payload, { timeout: 0 }).then((r) => r.data);

export interface BlogExportResult {
  ok: boolean;
  detail: string;
  sheet_url: string | null;
}

export const exportBlogPostsToSheet = (siteId: number) =>
  api.post<BlogExportResult>("/api/seo/blog/export-to-sheet", { site_id: siteId }).then((r) => r.data);

// Generates a featured image (via the app's image provider factory),
// converts it to WebP, uploads it to the site's own server (Server
// Access must be configured), and attaches the resulting URL to the
// post. A 502 means no image provider or no server access is
// configured yet — see api/routes/seo.py's generate_blog_post_image_route.
export const generateBlogPostImage = (postId: number, prompt?: string) =>
  api.post<BlogPost>(`/api/seo/blog/${postId}/image/generate`, { prompt }, { timeout: 60_000 }).then((r) => r.data);

export const generateSocialPostImage = (postId: number, prompt?: string) =>
  api.post<SocialPost>(`/api/seo/social/${postId}/image/generate`, { prompt }, { timeout: 60_000 }).then((r) => r.data);

// Manual image upload — same WebP-conversion-then-upload-to-the-site
// pipeline as the generate endpoints above, for a file picked from the
// user's own computer instead of one the AI generated.
export const uploadBlogPostImage = (postId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<BlogPost>(`/api/seo/blog/${postId}/image/upload`, form, { timeout: 60_000 })
    .then((r) => r.data);
};

export const uploadSocialPostImage = (postId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<SocialPost>(`/api/seo/social/${postId}/image/upload`, form, { timeout: 60_000 })
    .then((r) => r.data);
};

export interface OgTags {
  id: number;
  site_id: number;
  page_url: string;
  page_title: string;
  og_title: string;
  og_description: string;
  generated_at: string | null;
}

export const generateOgTags = (payload: { site_id: number; page_url: string; page_title: string; content_excerpt: string }) =>
  api.post<OgTags>("/api/seo/og-tags/generate", payload).then((r) => r.data);

export interface RelatedPage {
  url: string;
  title: string;
  distance: number;
}

export const suggestInterlinks = (payload: { site_id: number; url: string; title: string; content: string; n_results?: number }) =>
  api.post<RelatedPage[]>("/api/seo/interlinks/suggest", payload).then((r) => r.data);

// Embeds this page's content into the interlink vector index so FUTURE
// posts' suggestInterlinks calls can find it — call after publishing or
// materially editing a page. The blog publish flow already does this
// automatically for posts it publishes itself; this is for anything
// edited directly in the CMS.
export const indexPageForInterlinks = (payload: { site_id: number; url: string; title: string; content: string }) =>
  api.post<{ indexed: boolean; url: string }>("/api/seo/interlinks/index", payload).then((r) => r.data);

export interface StructureReport {
  word_count: number;
  h1_count: number;
  h2_count: number;
  h3_count: number;
  passed: boolean;
  issues: StructureIssue[];
}

export const analyzeContentStructure = (payload: { content_html: string; primary_keyword?: string; min_words?: number; max_words?: number }) =>
  api.post<StructureReport>("/api/seo/content/analyze", payload).then((r) => r.data);

export interface FaqPair {
  question: string;
  answer: string;
}

// Seeds the FAQ with this site's own real GSC search queries server-side
// — only site_id/page_title/max_pairs need to be supplied here.
export const generateFaq = (payload: { site_id: number; page_title: string; max_pairs?: number }) =>
  api.post<FaqPair[]>("/api/seo/content/faq", payload, { timeout: 60_000 }).then((r) => r.data);

// Module 39 — bulk CMS image-to-WebP conversion. Scans every published
// post/page for JPG/PNG <img src>/<img srcset> references, converts
// each to WebP, uploads it alongside the original (nothing deleted),
// and rewrites the post to point at the new file. dry_run (default
// true) reports exactly what would happen without changing anything —
// always run that first. A content backup is saved automatically
// before every real rewrite (see getContentBackups/getContentBackup).
export interface PostConversionDetail {
  post_id: string;
  kind: string;
  title: string;
  image_urls_found: string[];
  images_converted: number;
  images_cached: number;
  images_failed: number;
  content_changed: boolean;
  updated: boolean;
  backup_id: number | null;
  error: string | null;
}

export interface BulkConvertReport {
  dry_run: boolean;
  posts_scanned: number;
  posts_with_images: number;
  posts_updated: number;
  images_found: number;
  images_converted: number;
  images_cached: number;
  images_failed: number;
  error: string | null;
  details: PostConversionDetail[];
}

export const runWebpBulkConvert = (siteId: number, dryRun: boolean) =>
  api
    .post<BulkConvertReport>("/api/seo/webp-convert", { site_id: siteId, dry_run: dryRun }, { timeout: 300_000 })
    .then((r) => r.data);

// Per-URL alternative — converts images on one specific page instead of
// scanning the whole site. Resolves the URL to its actual CMS post
// first (by ?p=id or by slug), then runs the same conversion logic.
export const runWebpConvertUrl = (siteId: number, url: string, dryRun: boolean) =>
  api
    .post<BulkConvertReport>("/api/seo/webp-convert/url", { site_id: siteId, url, dry_run: dryRun }, { timeout: 120_000 })
    .then((r) => r.data);

export interface ContentBackupSummary {
  id: number;
  site_id: number;
  cms_post_id: string;
  kind: string;
  reason: string;
  created_at: string | null;
}

export interface ContentBackup extends ContentBackupSummary {
  original_content: string;
}

export const getContentBackups = (siteId: number, cmsPostId?: string) =>
  api
    .get<ContentBackupSummary[]>("/api/seo/webp-convert/backups", { params: { site_id: siteId, cms_post_id: cmsPostId } })
    .then((r) => r.data);

export const getContentBackup = (backupId: number) =>
  api.get<ContentBackup>(`/api/seo/webp-convert/backups/${backupId}`).then((r) => r.data);

// ── URL Redirection (api/routes/redirects.py) ──

export type RedirectStatusCode = 301 | 302;

// "served" = this API answers the URL, "synced" = written into the site's own
// .htaccess and verified live, "pending" = not applied yet, "failed" = applying
// was rolled back, "unmanaged" = nothing enforces it yet.
export type RedirectSyncStatus = "served" | "synced" | "pending" | "failed" | "unmanaged";

export interface UrlRedirect {
  id: number;
  source_url: string;
  source_host: string | null;
  source_path: string;
  target_url: string;
  status_code: RedirectStatusCode;
  hit_count: number;
  last_hit_at: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  live_url: string;
  sync_status: RedirectSyncStatus;
  sync_message: string;
  synced_at: string | null;
  apply_site: string | null;
}

export interface RedirectInput {
  source_url: string;
  target_url: string;
  status_code: RedirectStatusCode;
}

export interface RedirectTestResult {
  ok: boolean;
  probed_url: string;
  status_code: number | null;
  location: string | null;
  message: string;
}

export const getRedirects = () => api.get<UrlRedirect[]>("/api/redirects").then((r) => r.data);

// Saving/removing a rule for a real site writes its .htaccess over FTP/SFTP and
// verifies it with live requests — allow well beyond the default 15s timeout.
const REDIRECT_SYNC_TIMEOUT_MS = 120_000;

export const createRedirect = (payload: RedirectInput) =>
  api.post<UrlRedirect>("/api/redirects", payload, { timeout: REDIRECT_SYNC_TIMEOUT_MS }).then((r) => r.data);

export const updateRedirect = (id: number, payload: Partial<RedirectInput>) =>
  api.put<UrlRedirect>(`/api/redirects/${id}`, payload, { timeout: REDIRECT_SYNC_TIMEOUT_MS }).then((r) => r.data);

export const deleteRedirect = (id: number) =>
  api.delete(`/api/redirects/${id}`, { timeout: REDIRECT_SYNC_TIMEOUT_MS });

export const applyRedirect = (id: number) =>
  api.post<UrlRedirect>(`/api/redirects/${id}/apply`, null, { timeout: REDIRECT_SYNC_TIMEOUT_MS }).then((r) => r.data);

export const testRedirect = (id: number) =>
  api.post<RedirectTestResult>(`/api/redirects/${id}/test`, null, { timeout: 20_000 }).then((r) => r.data);
