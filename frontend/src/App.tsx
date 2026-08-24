import { BrowserRouter as Router, Routes, Route } from "react-router";

import NotFound from "./pages/OtherPage/NotFound";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import { ProtectedRoute, OversightRoute } from "./components/auth/ProtectedRoute";
import LoginPage from "./pages/AuthPages/LoginPage";
import DashboardHome from "./pages/Dashboard/Home";
import TimelinePage from "./pages/Timeline/TimelinePage";
import AnalyticsPage from "./pages/Analytics/AnalyticsPage";
import ScreenshotsPage from "./pages/Screenshots/ScreenshotsPage";
import ReportsPage from "./pages/Reports/ReportsPage";
import SettingsPage from "./pages/Settings/SettingsPage";
import CommandModePage from "./pages/CommandMode/CommandModePage";
import LinkedInPage from "./pages/LinkedIn/LinkedInPage";
import EmailPage from "./pages/Email/EmailPage";
import TeamPage from "./pages/Team/TeamPage";
import AttendancePage from "./pages/Attendance/AttendancePage";

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index path="/" element={<DashboardHome />} />

            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="/attendance" element={<AttendancePage />} />
            <Route path="/screenshots" element={<ScreenshotsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/command" element={<CommandModePage />} />
            <Route path="/linkedin" element={<LinkedInPage />} />
            <Route path="/email" element={<EmailPage />} />
            <Route element={<OversightRoute />}>
              <Route path="/team" element={<TeamPage />} />
            </Route>
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
