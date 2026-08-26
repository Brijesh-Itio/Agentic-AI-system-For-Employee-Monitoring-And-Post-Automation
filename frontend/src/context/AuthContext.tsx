import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe, login as apiLogin, logout as apiLogout, onUnauthorized, setAuthToken, type TeamUser } from "@/api";

const TOKEN_STORAGE_KEY = "workpulse_token";

interface AuthContextValue {
  user: TeamUser | null;
  token: string | null;
  isLoading: boolean;
  isOversight: boolean; // manager or admin
  isAdmin: boolean;
  login: (userId: string, password: string) => Promise<void>;
  loginWithToken: (accessToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TeamUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_STORAGE_KEY));
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setAuthToken(null);
    setToken(null);
    setUser(null);
  };

  useEffect(() => {
    onUnauthorized(clearSession);
  }, []);

  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    setAuthToken(token);
    getMe()
      .then(setUser)
      .catch(() => clearSession())
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (userId: string, password: string) => {
    const result = await apiLogin(userId, password);
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    setAuthToken(result.access_token);
    setToken(result.access_token);
    setUser(result.user);
  };

  // For SSO: the backend already issued a token (via the Google OAuth
  // redirect flow) — this just adopts it, fetching /me to populate the
  // user the same way the token-restore effect above does on page load.
  const loginWithToken = async (accessToken: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setAuthToken(accessToken);
    const me = await getMe();
    setToken(accessToken);
    setUser(me);
  };

  const logout = () => {
    apiLogout().catch(() => {
      /* stateless token — a failed logout call still ends the local session */
    });
    clearSession();
  };

  const isOversight = user?.role === "manager" || user?.role === "admin";
  const isAdmin = user?.role === "admin";

  return (
    <AuthContext.Provider value={{ user, token, isLoading, isOversight, isAdmin, login, loginWithToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
