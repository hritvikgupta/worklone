import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Search, CheckCircle2, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { IntegrationIcon } from '@/src/components/IntegrationIcon';
import {
  getIntegrations,
  disconnectIntegration,
  getOAuthUrl,
  saveOAuthProviderCredentials,
  saveProviderApiKey,
  AUTH_EXPIRED_ERROR,
  type IntegrationStatus,
  type IntegrationField,
} from '@/lib/auth-api';

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  google: 'Connect Gmail for email integration and communication.',
  slack: 'Connect Slack for team notifications and messaging.',
  notion: 'Connect Notion for docs, PRDs, and roadmaps.',
  github: 'Connect GitHub for issues, PRs, and repo sync.',
  jira: 'Connect Jira for backlog and sprint management.',
  salesforce: 'Connect Salesforce for CRM, leads, and opportunity management.',
  linear: 'Connect Linear for modern software project management.',
  hubspot: 'Connect Hubspot for marketing, sales, and service tools.',
  stripe: 'Connect Stripe for payments, billing, and subscription management.',
  google_drive: 'Connect Google Drive for file storage, sharing, and document management.',
  google_calendar: 'Connect Google Calendar for event scheduling, availability, and calendar management.',
};

// IDs now handled as real integrations (OAuth or API key) — kept out of coming soon
const CONFIGURED_INTEGRATION_IDS = new Set([
  // OAuth providers (original)
  "google","slack","notion","github","jira","salesforce","linear","hubspot","stripe","google_drive","google_calendar",
  // OAuth providers (new)
  "airtable","asana","attio","box","box_sign","calcom","dropbox",
  "google_ads","google_bigquery","google_docs","google_forms","google_meet","google_sheets","google_slides","google_tasks",
  // API key providers
  "agentmail","ahrefs","airweave","apollo","ashby","cursor","datadog","devin","discord",
  "evernote","exa","extend","firecrawl","gamma","gitlab","gong","google_maps","granola",
  "greenhouse","hex","hunter","incidentio","intercom","kalshi","langsmith","loops","luma",
  "pagerduty","reducto","sixtyfour","trello","vercel","youtube","zendesk","zep",
  // Infrastructure / connection providers
  "aws","neo4j","postgresql","redis","databricks","workday","video","sms",
]);

const COMING_SOON_PRIORITY = [{ id: "salesforce", name: "Salesforce" }];

export function Integrations() {
  const { token, logout } = useAuth();
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [simToolCatalog, setSimToolCatalog] = useState<Array<{ id: string; name: string }>>([]);
  const [deploymentMode, setDeploymentMode] = useState<'cloud' | 'self_hosted'>('self_hosted');
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [credentialModalOpen, setCredentialModalOpen] = useState(false);
  const [pendingProvider, setPendingProvider] = useState<IntegrationStatus | null>(null);
  const [clientIdInput, setClientIdInput] = useState('');
  const [clientSecretInput, setClientSecretInput] = useState('');
  const [savingCredentials, setSavingCredentials] = useState(false);
  // API key modal state
  const [apiKeyModalOpen, setApiKeyModalOpen] = useState(false);
  const [apiKeyProvider, setApiKeyProvider] = useState<IntegrationStatus | null>(null);
  const [apiKeyInputs, setApiKeyInputs] = useState<Record<string, string>>({});
  const [savingApiKey, setSavingApiKey] = useState(false);

  useEffect(() => {
    if (token) {
      getIntegrations(token)
        .then((data) => {
          setIntegrations(data.integrations);
          setDeploymentMode(data.deployment_mode);
        })
        .catch((error) => {
          if (error instanceof Error && error.message === AUTH_EXPIRED_ERROR) {
            logout();
          }
        })
        .finally(() => setLoading(false));
    }
  }, [token, logout]);

  useEffect(() => {
    let cancelled = false;
    fetch('/integrations/sim-tools.json')
      .then((res) => (res.ok ? res.json() : []))
      .then((rows: Array<{ id: string; name: string }>) => {
        if (!cancelled && Array.isArray(rows)) {
          setSimToolCatalog(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSimToolCatalog([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const startOAuthConnect = async (provider: string) => {
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
        return;
      }
      setConnectError(error instanceof Error ? error.message : `Failed to connect ${provider}`);
    } finally {
      setConnecting(null);
    }
  };

  const handleConnect = async (provider: string) => {
    setConnectError(null);
    const integration = integrations.find((item) => item.id === provider);
    if (!integration) {
      setConnectError(`Unknown integration provider: ${provider}`);
      return;
    }

    // API key provider — show API key modal
    if (integration.auth_type === 'api_key') {
      setApiKeyProvider(integration);
      setApiKeyInputs({});
      setApiKeyModalOpen(true);
      return;
    }

    if (
      deploymentMode === 'self_hosted'
      && integration.client_credentials_required
      && !integration.has_client_credentials
    ) {
      setPendingProvider(integration);
      setClientIdInput('');
      setClientSecretInput('');
      setCredentialModalOpen(true);
      return;
    }

    await startOAuthConnect(provider);
  };

  const handleSaveApiKey = async () => {
    if (!apiKeyProvider || !token) return;
    setSavingApiKey(true);
    setConnectError(null);
    try {
      const saved = await saveProviderApiKey(token, apiKeyProvider.id, apiKeyInputs);
      if (!saved) {
        setConnectError(`Failed to save API key for ${apiKeyProvider.name}.`);
        return;
      }
      setIntegrations((prev) =>
        prev.map((item) => item.id === apiKeyProvider.id ? { ...item, connected: true } : item)
      );
      setApiKeyModalOpen(false);
      setApiKeyProvider(null);
      setApiKeyInputs({});
    } finally {
      setSavingApiKey(false);
    }
  };

  const closeCredentialModal = () => {
    if (savingCredentials) return;
    setCredentialModalOpen(false);
    setPendingProvider(null);
    setClientIdInput('');
    setClientSecretInput('');
  };

  const handleSaveCredentialsAndConnect = async () => {
    if (!pendingProvider || !token) return;
    const clientId = clientIdInput.trim();
    const clientSecret = clientSecretInput.trim();
    if (!clientId) {
      setConnectError(`OAuth client ID is required for ${pendingProvider.name}.`);
      return;
    }
    if (!clientSecret) {
      setConnectError(`OAuth client secret is required for ${pendingProvider.name}.`);
      return;
    }

    setSavingCredentials(true);
    setConnectError(null);
    try {
      const saved = await saveOAuthProviderCredentials(token, pendingProvider.id, clientId, clientSecret);
      if (!saved) {
        setConnectError(`Failed to save OAuth credentials for ${pendingProvider.name}.`);
        return;
      }
      setIntegrations((prev) =>
        prev.map((item) =>
          item.id === pendingProvider.id ? { ...item, has_client_credentials: true } : item,
        ),
      );
      setCredentialModalOpen(false);
      const providerId = pendingProvider.id;
      setPendingProvider(null);
      setClientIdInput('');
      setClientSecretInput('');
      await startOAuthConnect(providerId);
    } finally {
      setSavingCredentials(false);
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

  const filteredIntegrations = integrations.filter(int => 
    int.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
    (PROVIDER_DESCRIPTIONS[int.id] || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const configuredIds = new Set(integrations.map((i) => i.id));
  const catalogFallback = simToolCatalog.length ? simToolCatalog : [];
  const mergedComingSoon = [...COMING_SOON_PRIORITY, ...catalogFallback.filter((int) => int.id !== "salesforce")]
    .filter((int) => !configuredIds.has(int.id) && !CONFIGURED_INTEGRATION_IDS.has(int.id));
  const filteredComingSoon = mergedComingSoon.filter(int =>
    int.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto bg-[#FAFAFA]">
      {credentialModalOpen && pendingProvider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Add OAuth Keys</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  {pendingProvider.name}: enter your OAuth client ID and client secret.
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={closeCredentialModal}
                disabled={savingCredentials}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-foreground">Client ID</label>
                <input
                  type="text"
                  value={clientIdInput}
                  onChange={(e) => setClientIdInput(e.target.value)}
                  placeholder={`Paste ${pendingProvider.name} OAuth client ID`}
                  className="w-full h-10 rounded-lg border border-border bg-white px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  disabled={savingCredentials}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-foreground">Client Secret</label>
                <input
                  type="password"
                  value={clientSecretInput}
                  onChange={(e) => setClientSecretInput(e.target.value)}
                  placeholder={`Paste ${pendingProvider.name} OAuth client secret`}
                  className="w-full h-10 rounded-lg border border-border bg-white px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                  disabled={savingCredentials}
                />
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={closeCredentialModal} disabled={savingCredentials}>
                Cancel
              </Button>
              <Button onClick={handleSaveCredentialsAndConnect} disabled={savingCredentials}>
                {savingCredentials ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save & Connect'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* API Key Modal */}
      {apiKeyModalOpen && apiKeyProvider && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-white p-5 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-foreground">Connect {apiKeyProvider.name}</h3>
                <p className="text-xs text-muted-foreground mt-1">Enter your API credentials to connect.</p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => { setApiKeyModalOpen(false); setApiKeyProvider(null); setApiKeyInputs({}); }}
                disabled={savingApiKey}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="space-y-3">
              {(apiKeyProvider.fields || []).map((field) => (
                <div key={field.key}>
                  <label className="mb-1 block text-xs font-medium text-foreground">
                    {field.label}{field.required && <span className="text-destructive ml-0.5">*</span>}
                  </label>
                  <input
                    type={field.secret ? 'password' : 'text'}
                    value={apiKeyInputs[field.key] || ''}
                    onChange={(e) => setApiKeyInputs((prev) => ({ ...prev, [field.key]: e.target.value }))}
                    placeholder={`Enter ${field.label}`}
                    className="w-full h-10 rounded-lg border border-border bg-white px-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                    disabled={savingApiKey}
                  />
                </div>
              ))}
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setApiKeyModalOpen(false); setApiKeyProvider(null); setApiKeyInputs({}); }} disabled={savingApiKey}>
                Cancel
              </Button>
              <Button onClick={handleSaveApiKey} disabled={savingApiKey}>
                {savingApiKey ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save & Connect'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="p-8 max-w-[1600px] mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">

        {/* Header & Search */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Integrations</h1>
            <p className="text-sm text-muted-foreground">Connect external tools to give Katy the ability to execute work seamlessly.</p>
            <p className="text-xs text-muted-foreground">
              Mode: <span className="font-medium text-foreground">{deploymentMode === 'cloud' ? 'Cloud (managed keys)' : 'Self-hosted (bring your own OAuth keys)'}</span>
            </p>
          </div>
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search integrations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-4 rounded-lg border border-border bg-white text-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all shadow-sm"
            />
          </div>
        </div>

        {connectError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {connectError}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-10">
            
            {/* Active Integrations */}
            {(filteredIntegrations.length > 0 || searchQuery === '') && (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-3">
                  Available Integrations
                  <span className="h-px flex-1 bg-border/40"></span>
                </h2>
                
                {filteredIntegrations.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
                    {filteredIntegrations.map((integration) => (
                      <div key={integration.id} className="bg-white border border-border/60 rounded-xl p-4 flex items-center gap-4 hover:shadow-sm transition-all group">
                        <IntegrationIcon id={integration.id} name={integration.name} className="w-10 h-10 shrink-0 shadow-sm" />
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold text-foreground truncate">{integration.name}</h3>
                            {integration.connected && (
                              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                            )}
                          </div>
                          {integration.connected && integration.provider_email ? (
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5" title={integration.provider_email}>
                              {integration.provider_email}
                            </p>
                          ) : (
                            <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                              {integration.connected ? 'Connected' : 'Not connected'}
                            </p>
                          )}
                          {deploymentMode === 'self_hosted' && integration.client_credentials_required && !integration.has_client_credentials && (
                            <p className="text-[11px] text-amber-600 truncate mt-0.5">
                              OAuth app keys required before connect
                            </p>
                          )}
                        </div>

                        <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          {integration.connected ? (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDisconnect(integration.id)}
                              className="h-8 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                            >
                              Disconnect
                            </Button>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleConnect(integration.id)}
                              disabled={connecting === integration.id}
                              className="h-8 px-3 text-xs bg-zinc-100 hover:bg-zinc-200 text-zinc-900 border-border/50"
                            >
                              {connecting === integration.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Connect'}
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No available integrations found matching "{searchQuery}".</p>
                )}
              </div>
            )}

            {/* Coming Soon Integrations */}
            {(filteredComingSoon.length > 0 || searchQuery === '') && (
              <div className="space-y-4">
                <h2 className="text-sm font-semibold text-muted-foreground flex items-center gap-3">
                  Coming Soon
                  <span className="h-px flex-1 bg-border/40"></span>
                </h2>
                
                {filteredComingSoon.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
                    {filteredComingSoon.map((integration) => (
                      <div key={integration.id} className="bg-zinc-50/50 border border-border/40 rounded-xl p-3 flex items-center gap-3 opacity-60 grayscale-[80%] hover:grayscale-[50%] transition-all cursor-not-allowed">
                        <IntegrationIcon id={integration.id} name={integration.name} className="w-8 h-8 shrink-0 shadow-sm" />
                        <div className="flex-1 min-w-0">
                          <h3 className="text-xs font-semibold text-zinc-700 truncate">{integration.name}</h3>
                          <p className="text-[10px] text-zinc-500 mt-0.5">Coming soon</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No coming soon integrations found matching "{searchQuery}".</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
