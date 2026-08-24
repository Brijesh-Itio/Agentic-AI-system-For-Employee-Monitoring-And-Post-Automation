import { useState } from "react";
import { useNavigate } from "react-router";
import { ChevronDown, LogOut, Settings } from "lucide-react";
import { DropdownItem } from "../ui/dropdown/DropdownItem";
import { Dropdown } from "../ui/dropdown/Dropdown";
import { useAuth } from "@/context/AuthContext";

const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  manager: "Manager",
  employee: "Employee",
};

export default function UserDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const initial = user.name.trim().charAt(0).toUpperCase() || "?";

  const handleLogout = () => {
    setIsOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="dropdown-toggle flex items-center gap-2.5 text-gray-700 dark:text-gray-400"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-indigo-600 text-sm font-semibold text-white">
          {initial}
        </span>
        <span className="hidden text-theme-sm font-medium sm:block">{user.name}</span>
        <ChevronDown
          className={`h-4 w-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      <Dropdown
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        className="absolute right-0 mt-[17px] flex w-[240px] flex-col rounded-2xl border border-gray-200 bg-white p-3 shadow-theme-lg dark:border-gray-800 dark:bg-gray-dark"
      >
        <div className="px-1 pb-3">
          <span className="block text-theme-sm font-medium text-gray-700 dark:text-gray-300">
            {user.name}
          </span>
          <span className="mt-0.5 block text-theme-xs text-gray-500 dark:text-gray-400">
            {ROLE_LABEL[user.role] ?? user.role} · {user.id}
          </span>
        </div>
        <DropdownItem
          onItemClick={() => setIsOpen(false)}
          tag="a"
          to="/settings"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-theme-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
        >
          <Settings className="h-4.5 w-4.5" />
          Settings
        </DropdownItem>
        <button
          onClick={handleLogout}
          className="mt-1 flex items-center gap-3 rounded-lg px-3 py-2 text-left text-theme-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/5"
        >
          <LogOut className="h-4.5 w-4.5" />
          Sign Out
        </button>
      </Dropdown>
    </div>
  );
}
