/**
 * Auth API functions
 */

import { BACKEND_URL } from './api';

export const AUTH_EXPIRED_ERROR = 'AUTH_EXPIRED';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  user?: AuthUser;
  error?: string;
}

/**
 * Register a new user
 */
export async function register(email: string, password: string, name: string): Promise<AuthResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });

    return await response.json();
  } catch (error) {
    console.error('Register error:', error);
    return { success: false, error: 'Registration failed' };
  }
}

/**
 * Login user
 */
export async function login(email: string, password: string): Promise<AuthResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    return await response.json();
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: 'Login failed' };
  }
}

/**
 * Get current user
 */
export async function getCurrentUser(token: string): Promise<AuthUser | null> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) return null;
    const data = await response.json();
    return data.user;
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Get user error:', error);
    return null;
  }
}

/**
 * Logout user
 */
export async function logout(token: string): Promise<void> {
  try {
    await fetch(`${BACKEND_URL}/api/auth/logout`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    });
  } catch (error) {
    console.error('Logout error:', error);
  }
}

/**
 * Get OAuth authorization URL
 */
export async function getOAuthUrl(token: string, provider: string, frontendUrl: string): Promise<string | null> {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/integrations/authorize?provider=${provider}&frontend_url=${encodeURIComponent(frontendUrl)}`,
      {
        headers: { 'Authorization': `Bearer ${token}` },
      }
    );

    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) return null;
    const data = await response.json();
    return data.auth_url;
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Get OAuth URL error:', error);
    return null;
  }
}

/**
 * Get integration statuses
 */
export interface IntegrationStatus {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
  connected_at?: string;
  provider_email?: string;
}

export async function getIntegrations(token: string): Promise<IntegrationStatus[]> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/integrations/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) return [];
    const data = await response.json();
    return data.integrations || [];
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Get integrations error:', error);
    return [];
  }
}

/**
 * Disconnect an integration
 */
export async function disconnectIntegration(token: string, provider: string): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/integrations/${provider}/disconnect`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    return response.ok;
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Disconnect integration error:', error);
    return false;
  }
}
