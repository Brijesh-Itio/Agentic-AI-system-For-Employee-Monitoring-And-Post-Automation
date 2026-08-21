import { useState } from "react";
import { ChevronDown, Settings } from "lucide-react";
import { DropdownItem } from "../ui/dropdown/DropdownItem";
import { Dropdown } from "../ui/dropdown/Dropdown";

// No multi-user auth system exists yet (api/middleware/auth.py is an
// unbuilt stub) — this reflects the single local tracked user
// (agent/config.py's default USER_ID="local"), not a fake login identity.
export default function UserDropdown() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="dropdown-toggle flex items-center gap-2.5 text-gray-700 dark:text-gray-400"
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-indigo-600 text-sm font-semibold text-white">
          L
        </span>
        <span className="hidden text-theme-sm font-medium sm:block">Local User</span>
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
            Local User
          </span>
          <span className="mt-0.5 block text-theme-xs text-gray-500 dark:text-gray-400">
            Tracked on this device
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
      </Dropdown>
    </div>
  );
}
