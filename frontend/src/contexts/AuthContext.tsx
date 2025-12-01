import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { StaffRole } from "@/types/staffUser";

type AuthUser = {
  id: number;
  username: string;
  full_name: string;
  role: StaffRole;
};

type AuthContextType = {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const STORAGE_KEY = "auth_user";

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as AuthUser;
        setUser(parsed);
      } catch (error) {
        console.error("Error parsing auth user", error);
      }
    }
  }, []);

  const login = async (username: string, password: string) => {
    const response = await api.post<AuthUser>("/auth/login/", { username, password });
    setUser(response.data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(response.data));
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout/");
    } catch (error) {
      console.error("Error logging out", error);
    }

    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    navigate("/login", { replace: true });
  };

  const value = useMemo(() => ({ user, login, logout }), [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
};
