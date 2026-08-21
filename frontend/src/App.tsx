import { BrowserRouter as Router, Routes, Route } from "react-router";
import {
  Terminal,
  Briefcase,
  Mail,
  Users,
} from "lucide-react";

import NotFound from "./pages/OtherPage/NotFound";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import ComingSoon from "./pages/ComingSoon";
import DashboardHome from "./pages/Dashboard/Home";
import TimelinePage from "./pages/Timeline/TimelinePage";
import AnalyticsPage from "./pages/Analytics/AnalyticsPage";
import ScreenshotsPage from "./pages/Screenshots/ScreenshotsPage";
import ReportsPage from "./pages/Reports/ReportsPage";
import SettingsPage from "./pages/Settings/SettingsPage";

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route element={<AppLayout />}>
          <Route index path="/" element={<DashboardHome />} />

          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/screenshots" element={<ScreenshotsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route
            path="/command"
            element={
              <ComingSoon
                title="Command Mode"
                moduleLabel="Module 17"
                description="Type any instruction and the Master Agent executes it across the system."
                icon={Terminal}
              />
            }
          />
          <Route
            path="/linkedin"
            element={
              <ComingSoon
                title="LinkedIn"
                moduleLabel="Module 18"
                description="Autonomous LinkedIn content writing and posting via Playwright."
                icon={Briefcase}
              />
            }
          />
          <Route
            path="/email"
            element={
              <ComingSoon
                title="Email"
                moduleLabel="Module 19"
                description="RAG-personalised lead outreach campaigns sent via Gmail SMTP."
                icon={Mail}
              />
            }
          />
          <Route
            path="/team"
            element={
              <ComingSoon
                title="Team"
                moduleLabel="Module 21"
                description="Manager view of every team member's activity and AI-generated insights."
                icon={Users}
              />
            }
          />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}
