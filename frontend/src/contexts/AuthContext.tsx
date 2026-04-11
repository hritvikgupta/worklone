/**
 * Auth Context - Global authentication state
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthUser } from '@/lib/auth-api';
import * as authApi from '@/lib/auth-api';

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, name: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearAuthState = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
  };

  // Load user from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('auth_token');
    if (savedToken) {
      setToken(savedToken);
      authApi.getCurrentUser(savedToken).then(user => {
        setUser(user);
        setIsLoading(false);
      }).catch(() => {
        clearAuthState();
        setIsLoading(false);
      });
    } else {
      setIsLoading(false);
    }
  }, []);

  // Periodically validate session; force logout if token expires server-side.
  useEffect(() => {
    if (!token) return;

    let isCancelled = false;
    const validateSession = async () => {
      try {
        const currentUser = await authApi.getCurrentUser(token);
        if (!currentUser && !isCancelled) {
          clearAuthState();
        } else if (currentUser && !isCancelled) {
          setUser(currentUser);
        }
      } catch {
        if (!isCancelled) {
          clearAuthState();
        }
      }
    };

    const intervalId = window.setInterval(validateSession, 5 * 60 * 1000);
    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
    };
  }, [token]);

  const login = async (email: string, password: string): Promise<boolean> => {
    const result = await authApi.login(email, password);
    if (result.success && result.token) {
      setToken(result.token);
      setUser(result.user || null);
      localStorage.setItem('auth_token', result.token);
      return true;
    }
    return false;
  };

  const register = async (email: string, password: string, name: string): Promise<boolean> => {
    const result = await authApi.register(email, password, name);
    if (result.success && result.token) {
      setToken(result.token);
      setUser(result.user || null);
      localStorage.setItem('auth_token', result.token);
      return true;
    }
    return false;
  };

  const logout = () => {
    if (token) {
      authApi.logout(token);
    }
    clearAuthState();
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      login,
      register,
      logout,
      isAuthenticated: !!user,
      isLoading,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
