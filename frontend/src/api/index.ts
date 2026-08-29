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

export const getAppsSummaryByDate = (date: string) =>
  api.get<AppSummary[]>("/api/activity/apps/summary", { params: { target_date: date } }).then((r) => r.data);

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

export const getMemberScreenshotsToday = (userId: string) =>
  api.get<ScreenshotEntry[]>(`/api/screenshots/member/${userId}/today`).then((r) => r.data);

export const getMemberScreenshotsByDate = (userId: string, date: string) =>
  api.get<ScreenshotEntry[]>(`/api/screenshots/member/${userId}/date/${date}`).then((r) => r.data);

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

export const exportDarUrl = (date: string, format: "csv" | "docx" | "pdf") =>
  `${API_BASE_URL}/api/reports/dar/date/${date}/export?format=${format}`;

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
// other on-demand generation endpoints.
export const getTeamAnalysis = (windowDays = 7) =>
  api
    .get<TeamAnalysis>("/api/team/analysis", { params: { window_days: windowDays }, timeout: 120_000 })
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

export type FeatureFlag = "screenshot_capture" | "activity_tracking" | "dar_generation" | "alerts_enabled";

export const FEATURE_FLAG_LABELS: Record<FeatureFlag, string> = {
  screenshot_capture: "Screenshot Capture",
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
