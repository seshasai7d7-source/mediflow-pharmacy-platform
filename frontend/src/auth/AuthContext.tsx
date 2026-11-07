
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  authApi,
  clearToken,
  getToken,
  saveToken,
  type LoginPayload,
  type RegisterPayload,
  type User,
} from "../lib/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  devLogin: () => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      const token = getToken();

      if (!token) {
        if (active) setLoading(false);
        return;
      }

      try {
        const currentUser = await authApi.getCurrentUser();

        if (active) {
          if (currentUser.is_active) {
            setUser(currentUser);
          } else {
            clearToken();
          }
        }
      } catch {
        clearToken();
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    }

    restoreSession();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const tokenResponse = await authApi.login(payload);

    saveToken(tokenResponse.access_token);

    try {
      const currentUser = await authApi.getCurrentUser();

      if (!currentUser.is_active) {
        throw new Error("This account is inactive. Please contact support.");
      }

      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearToken();
      setUser(null);
      throw error;
    }
  }, []);

  const devLogin = useCallback(async () => {
    const tokenResponse = await authApi.devLogin();

    saveToken(tokenResponse.access_token);

    try {
      const currentUser = await authApi.getCurrentUser();

      if (!currentUser.is_active || currentUser.role !== "customer") {
        throw new Error("Development customer account is unavailable.");
      }

      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearToken();
      setUser(null);
      throw error;
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    return authApi.register(payload);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: user !== null,
        login,
        devLogin,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }

  return context;
}
