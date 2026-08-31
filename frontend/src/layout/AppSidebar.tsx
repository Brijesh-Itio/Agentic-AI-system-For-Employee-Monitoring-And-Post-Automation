import { useCallback } from "react";
import { Link, useLocation } from "react-router";
import {
  LayoutDashboard,
  Clock,
  CalendarCheck,
  FileText,
  BarChart3,
  Terminal,
  Briefcase,
  Mail,
  Users,
  Settings as SettingsIcon,
  Zap,
} from "lucide-react";

import { HorizontaLDots } from "../icons";
import { useSidebar } from "../context/SidebarContext";
import SidebarWidget from "./SidebarWidget";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path: string;
};

const navItems: NavItem[] = [
  { icon: <LayoutDashboard />, name: "Dashboard", path: "/" },
  { icon: <Clock />, name: "Timeline", path: "/timeline" },
  { icon: <CalendarCheck />, name: "Attendance", path: "/attendance" },
  { icon: <FileText />, name: "Reports", path: "/reports" },
  { icon: <BarChart3 />, name: "Analytics", path: "/analytics" },
  { icon: <Terminal />, name: "Command Mode", path: "/command" },
  { icon: <Briefcase />, name: "LinkedIn", path: "/linkedin" },
  { icon: <Mail />, name: "Email", path: "/email" },
  { icon: <Users />, name: "Team", path: "/team" },
  { icon: <SettingsIcon />, name: "Settings", path: "/settings" },
];

const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const location = useLocation();

  const isActive = useCallback(
    (path: string) => location.pathname === path,
    [location.pathname]
  );

  const showLabels = isExpanded || isHovered || isMobileOpen;

  return (
    <aside
      className={`fixed mt-16 flex flex-col lg:mt-0 top-0 px-5 left-0 bg-white dark:bg-gray-900 dark:border-gray-800 text-gray-900 h-screen transition-all duration-300 ease-in-out z-50 border-r border-gray-200
        ${isExpanded || isMobileOpen ? "w-[290px]" : isHovered ? "w-[290px]" : "w-[90px]"}
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}
        lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className={`py-8 flex items-center ${!showLabels ? "lg:justify-center" : "justify-start"}`}>
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-indigo-600 text-white shadow-md shadow-brand-500/30">
            <Zap className="h-5 w-5" fill="currentColor" />
          </span>
          {showLabels && (
            <span className="text-base font-bold tracking-tight text-gray-900 dark:text-white">
              WorkPulse <span className="text-brand-500">AI</span>
            </span>
          )}
        </Link>
      </div>

      <div className="flex flex-col overflow-y-auto duration-300 ease-linear no-scrollbar">
        <nav className="mb-6">
          <div className="flex flex-col gap-4">
            <div>
              <h2
                className={`mb-4 text-xs uppercase flex leading-[20px] text-gray-400 ${
                  !showLabels ? "lg:justify-center" : "justify-start"
                }`}
              >
                {showLabels ? "Menu" : <HorizontaLDots className="size-6" />}
              </h2>
              <ul className="flex flex-col gap-1">
                {navItems.map((nav) => (
                  <li key={nav.name}>
                    <Link
                      to={nav.path}
                      className={`menu-item group ${
                        isActive(nav.path) ? "menu-item-active" : "menu-item-inactive"
                      }`}
                    >
                      <span
                        className={`menu-item-icon-size ${
                          isActive(nav.path) ? "menu-item-icon-active" : "menu-item-icon-inactive"
                        }`}
                      >
                        {nav.icon}
                      </span>
                      {showLabels && <span className="menu-item-text">{nav.name}</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </nav>
        {showLabels && <SidebarWidget />}
      </div>
    </aside>
  );
};

export default AppSidebar;
