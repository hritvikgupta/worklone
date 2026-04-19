/**
 * Auth API functions
 */

import { BACKEND_URL, errorMessageForCode, parseBackendError } from './api';

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
  error_code?: string;
  retryable?: boolean;
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

    if (!response.ok) {
      throw await parseBackendError(response, 'Registration failed.');
    }
    return await response.json();
  } catch (error) {
    console.error('Register error:', error);
    const code = error instanceof Error && 'code' in error && typeof error.code === 'string' ? error.code : 'AUTH_REGISTER_FAILED';
    return {
      success: false,
      error: errorMessageForCode(code, 'Registration failed'),
      error_code: code,
      retryable: true,
    };
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

    if (!response.ok) {
      throw await parseBackendError(response, 'Login failed.');
    }
    return await response.json();
  } catch (error) {
    console.error('Login error:', error);
    const code = error instanceof Error && 'code' in error && typeof error.code === 'string' ? error.code : 'AUTH_LOGIN_FAILED';
    return {
      success: false,
      error: errorMessageForCode(code, 'Login failed'),
      error_code: code,
      retryable: true,
    };
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
    if (!response.ok) {
      let errorMessage = `Failed to authorize ${provider}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData?.detail || errorData?.error || errorMessage;
      } catch {
        const errorText = await response.text();
        if (errorText) errorMessage = errorText;
      }
      throw new Error(errorMessage);
    }
    const data = await response.json();
    return data.auth_url;
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Get OAuth URL error:', error);
    throw error;
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
  client_credentials_required?: boolean;
  has_client_credentials?: boolean;
}

export interface IntegrationsResponse {
  integrations: IntegrationStatus[];
  deployment_mode: 'cloud' | 'self_hosted';
}

export async function getIntegrations(token: string): Promise<IntegrationsResponse> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/integrations/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    if (!response.ok) return { integrations: [], deployment_mode: 'self_hosted' };
    const data = await response.json();
    return {
      integrations: data.integrations || [],
      deployment_mode: data.deployment_mode === 'cloud' ? 'cloud' : 'self_hosted',
    };
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Get integrations error:', error);
    return { integrations: [], deployment_mode: 'self_hosted' };
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

export async function saveOAuthProviderCredentials(
  token: string,
  provider: string,
  clientId: string,
  clientSecret: string,
): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/integrations/credentials`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        provider,
        client_id: clientId,
        client_secret: clientSecret,
      }),
    });
    if (response.status === 401) {
      throw new Error(AUTH_EXPIRED_ERROR);
    }
    return response.ok;
  } catch (error) {
    if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
      throw error;
    }
    console.error('Save OAuth credentials error:', error);
    return false;
  }
}
