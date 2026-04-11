import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  Github,
  Slack,
  Mail,
  FileText,
  Briefcase,
  ExternalLink,
  CheckCircle2,
  Plus,
  Loader2,
  LogOut
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  getIntegrations,
  disconnectIntegration,
  getOAuthUrl,
  AUTH_EXPIRED_ERROR,
  type IntegrationStatus,
} from '@/lib/auth-api';

const PROVIDER_ICONS: Record<string, any> = {
  google: Mail,
  slack: Slack,
  notion: FileText,
  github: Github,
  jira: Briefcase,
};

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  google: 'Connect Gmail for email integration and communication.',
  slack: 'Connect Slack for team notifications and messaging.',
  notion: 'Connect Notion for docs, PRDs, and roadmaps.',
  github: 'Connect GitHub for issues, PRs, and repo sync.',
  jira: 'Connect Jira for backlog and sprint management.',
};

export function Integrations() {
  const { token, logout } = useAuth();
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    if (token) {
      getIntegrations(token)
        .then(setIntegrations)
        .catch((error) => {
          if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
            logout();
          }
        })
        .finally(() => setLoading(false));
    }
  }, [token, logout]);

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    const frontendUrl = window.location.origin;
    try {
      const authUrl = await getOAuthUrl(token!, provider, frontendUrl);
      if (authUrl) {
        window.location.href = authUrl;
      }
    } catch (error) {
      if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
        logout();
      }
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = async (provider: string) => {
    if (token) {
      try {
        await disconnectIntegration(token, provider);
        setIntegrations(prev =>
          prev.map(int => int.id === provider ? { ...int, connected: false } : int)
        );
      } catch (error) {
        if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
          logout();
        }
      }
    }
  };

  return (
    <div className="p-12 max-w-5xl mx-auto space-y-12">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight text-[#37352f]">Integrations</h1>
        <p className="text-zinc-500">Connect your external tools to Katy for a seamless workflow.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {integrations.map((integration) => {
            const Icon = PROVIDER_ICONS[integration.id] || ExternalLink;
            return (
              <div key={integration.id} className="bg-white border border-zinc-100 rounded-lg p-6 space-y-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)] hover:border-zinc-200 transition-all group">
                <div className="flex justify-between items-start">
                  <div className="w-10 h-10 rounded bg-zinc-50 flex items-center justify-center border border-zinc-100 group-hover:bg-zinc-100 transition-colors">
                    <Icon className="w-5 h-5 text-zinc-900" />
                  </div>
                  {integration.connected ? (
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                      <span className="text-[10px] font-bold uppercase tracking-wider text-green-700 bg-green-100/50 px-2 py-0.5 rounded">
                        Connected
                      </span>
                    </div>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-zinc-100 text-zinc-400">
                      Not Connected
                    </span>
                  )}
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#37352f]">{integration.name}</h3>
                  <p className="text-sm text-zinc-500 mt-1 leading-relaxed">
                    {PROVIDER_DESCRIPTIONS[integration.id] || integration.name}
                  </p>
                  {integration.connected && integration.provider_email && (
                    <p className="text-xs text-zinc-400 mt-1">
                      Connected as: {integration.provider_email}
                    </p>
                  )}
                </div>
                <div className="pt-2">
                  {integration.connected ? (
                    <Button
                      variant="outline"
                      onClick={() => handleDisconnect(integration.id)}
                      className="w-full h-9 text-sm font-medium border-zinc-100 text-zinc-600 hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-all"
                    >
                      <LogOut className="w-3.5 h-3.5 mr-1.5" />
                      Disconnect
                    </Button>
                  ) : (
                    <Button
                      onClick={() => handleConnect(integration.id)}
                      disabled={connecting === integration.id}
                      className="w-full h-9 text-sm font-medium bg-zinc-900 text-white hover:bg-zinc-800 disabled:opacity-50"
                    >
                      {connecting === integration.id ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        'Connect'
                      )}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="bg-zinc-50/50 border border-dashed border-zinc-200 rounded-lg p-8 text-center space-y-3">
        <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center mx-auto border border-zinc-100">
          <Plus className="w-5 h-5 text-zinc-400" />
        </div>
        <div className="space-y-1">
          <h3 className="text-sm font-bold text-[#37352f]">Request an Integration</h3>
          <p className="text-xs text-zinc-400">Don't see the tool you use? Let us know and we'll build it.</p>
        </div>
        <Button variant="ghost" className="text-xs text-zinc-500 hover:text-zinc-900">
          Submit Request
        </Button>
      </div>
    </div>
  );
}
