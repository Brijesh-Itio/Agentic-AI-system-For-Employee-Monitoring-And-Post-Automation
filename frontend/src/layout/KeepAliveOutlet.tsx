import { useRef, type ReactNode } from "react";
import { useLocation, useOutlet } from "react-router";

import { PageActiveProvider } from "@/context/PageActiveContext";

// Pages that keep running in the background once opened. Switching to another
// page used to unmount the current one, destroying the state that showed a
// running task (spinner, progress, the result that came back) even though the
// request itself carried on — so coming back looked like the task had
// stopped. Here a visited page stays mounted, just hidden, so a task started
// on it keeps going and is still there, in progress or finished, on return.
//
// Not included: /timeline (reads ?date= from the URL, which would change under
// it while hidden) and /team/:userId (one component serving many URLs).
const KEEP_ALIVE_PATHS = new Set([
  "/",
  "/attendance",
  "/reports",
  "/analytics",
  "/command",
  "/linkedin",
  "/email",
  "/seo",
  "/notepad",
  "/team",
  "/settings",
]);

export default function KeepAliveOutlet() {
  const { pathname } = useLocation();
  const outlet = useOutlet();
  const cache = useRef(new Map<string, ReactNode>());

  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const kept = KEEP_ALIVE_PATHS.has(path);
  if (kept && outlet) cache.current.set(path, outlet);

  return (
    <>
      {[...cache.current].map(([cachedPath, element]) => {
        const active = kept && cachedPath === path;
        return (
          <div key={cachedPath} hidden={!active}>
            <PageActiveProvider value={active}>{element}</PageActiveProvider>
          </div>
        );
      })}
      {!kept && outlet}
    </>
  );
}
