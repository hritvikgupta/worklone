import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { BACKEND_URL } from '@/lib/api';

type CallbackResponse = {
  success?: boolean;
  detail?: string;
  error?: string;
  message?: string;
};

let inFlightExchangeKey: string | null = null;
let inFlightExchangePromise: Promise<CallbackResponse> | null = null;

function exchangeOAuthCodeOnce(key: string, url: string): Promise<CallbackResponse> {
  if (inFlightExchangeKey === key && inFlightExchangePromise) {
    return inFlightExchangePromise;
  }

  inFlightExchangeKey = key;
  inFlightExchangePromise = fetch(url)
    .then(async (res) => {
      const data = await res.json().catch(() => ({} as CallbackResponse));
      if (!res.ok) {
        return {
          ...data,
          success: false,
          detail: data.detail || data.error || `Token exchange failed (${res.status})`,
        };
      }
      return data;
    })
    .finally(() => {
      inFlightExchangeKey = null;
      inFlightExchangePromise = null;
    });

  return inFlightExchangePromise;
}

export function IntegrationCallback() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Processing connection...');
  const search = useMemo(() => new URLSearchParams(window.location.search), []);

  useEffect(() => {
    const code = search.get('code');
    const state = search.get('state');
    const error = search.get('error');
    const stateParts = (state || '').split('::');
    const providerFromState = stateParts.length >= 3 ? stateParts[2] : '';
    const provider = search.get('provider') || providerFromState || 'github';

    if (error) {
      setStatus('error');
      setMessage(`Connection failed: ${error}`);
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setMessage('Missing connection details.');
      return;
    }

    const key = `${provider}:${code}:${state}`;
    const redirectUri = `${window.location.origin}/integrations/callback`;
    const callbackUrl = `${BACKEND_URL}/api/integrations/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}&provider=${encodeURIComponent(provider)}&redirect_uri=${encodeURIComponent(redirectUri)}`;

    // Exchange OAuth code exactly once per code/state/provider combo.
    exchangeOAuthCodeOnce(key, callbackUrl)
      .then((data) => {
        if (data.success) {
          setStatus('success');
          setMessage('Integration connected successfully!');
          setTimeout(() => {
            window.location.href = '/';
          }, 1500);
        } else {
          setStatus('error');
          setMessage(data.detail || data.error || 'Failed to save connection.');
        }
      })
      .catch(() => {
        setStatus('error');
        setMessage('Network error while connecting.');
      });
  }, [search]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted">
      <div className="bg-card p-8 rounded-xl shadow-lg border border-border text-center space-y-4">
        {status === 'loading' && (
          <Loader2 className="w-10 h-10 animate-spin mx-auto text-foreground" />
        )}
        {status === 'success' && (
          <CheckCircle className="w-10 h-10 mx-auto text-green-500" />
        )}
        {status === 'error' && (
          <XCircle className="w-10 h-10 mx-auto text-red-500" />
        )}
        <h2 className="text-lg font-bold text-foreground">
          {status === 'loading' ? 'Connecting...' : status === 'success' ? 'Connected!' : 'Error'}
        </h2>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}
