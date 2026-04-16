import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Search, CheckCircle2, Loader2, LogOut, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  getIntegrations,
  disconnectIntegration,
  getOAuthUrl,
  AUTH_EXPIRED_ERROR,
  type IntegrationStatus,
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

function getSimpleIconUrl(id: string): string {
  const overrides: Record<string, string> = {
    google: 'gmail/EA4333',
    slack: '/slackicon.png',
    notion: 'notion/000000',
    github: 'github/181717',
    jira: 'jira/0052CC',
    salesforce: 'salesforce/00A1E0',
    linear: 'linear/5E6AD2',
    hubspot: 'hubspot/FF7A59',
    stripe: 'stripe/635BFF',
    google_drive: 'googledrive/4285F4',
    google_calendar: 'googlecalendar/4285F4',
    aws: 'amazonaws/232F3E',
    zendesk: 'zendesk/03363D',
    confluence: 'confluence/172B4D',
    airtable: 'airtable/18BFFF',
    figma: 'figma/F24E1E',
    snowflake: 'snowflake/29B5E8',
    postgres: 'postgresql/4169E1',
    postgresql: 'postgresql/4169E1',
    bigquery: 'googlebigquery/669DF6',
    clickup: 'clickup/7B68EE',
    intercom: 'intercom/6AF13A',
    dropbox: 'dropbox/0061FF',
    trello: 'trello/0052CC',
    zapier: 'zapier/FF4A00',
    discord: 'discord/5865F2',
    vercel: 'vercel/000000',
    gitlab: 'gitlab/FC6D26',
    twilio: 'twilio/F22F46',
    shopify: 'shopify/95BF47',
    zoom: 'zoom/0B5CFF',
    asana: 'asana/F06A6A',
    x: 'x/000000',
    linkedin: 'linkedin/0A66C2',
    wordpress: 'wordpress/21759B',
    mailchimp: 'mailchimp/FFE01B',
    datadog: 'datadog/632CA6',
    cloudflare: 'cloudflare/F38020',
  };

  if (overrides[id]) {
    return overrides[id].startsWith('/') ? overrides[id] : `https://cdn.simpleicons.org/${overrides[id]}`;
  }
  return `https://cdn.simpleicons.org/${id.replace(/_/g, '')}/71717A`; 
}

function IntegrationIcon({ id, name, className }: { id: string; name: string; className?: string }) {
  const [error, setError] = useState(false);
  const iconUrl = getSimpleIconUrl(id);

  if (error) {
    return (
      <div className={cn("flex items-center justify-center rounded-md border border-border bg-muted text-[10px] font-semibold text-muted-foreground", className)}>
        {name.slice(0, 2).toUpperCase()}
      </div>
    );
  }

  return (
    <img
      src={iconUrl}
      alt={`${name} icon`}
      className={cn("object-contain rounded-md", className)}
      onError={() => setError(true)}
    />
  );
}

const COMING_SOON_INTEGRATIONS = [{"id": "a2a", "name": "A2A"}, {"id": "agentmail", "name": "Agentmail"}, {"id": "ahrefs", "name": "Ahrefs"}, {"id": "airtable", "name": "Airtable"}, {"id": "airweave", "name": "Airweave"}, {"id": "algolia", "name": "Algolia"}, {"id": "amplitude", "name": "Amplitude"}, {"id": "apify", "name": "Apify"}, {"id": "apollo", "name": "Apollo"}, {"id": "arxiv", "name": "Arxiv"}, {"id": "asana", "name": "Asana"}, {"id": "ashby", "name": "Ashby"}, {"id": "attio", "name": "Attio"}, {"id": "box", "name": "Box"}, {"id": "box_sign", "name": "Box Sign"}, {"id": "brandfetch", "name": "Brandfetch"}, {"id": "browser_use", "name": "Browser Use"}, {"id": "calcom", "name": "Calcom"}, {"id": "calendly", "name": "Calendly"}, {"id": "clay", "name": "Clay"}, {"id": "clerk", "name": "Clerk"}, {"id": "cloudflare", "name": "Cloudflare"}, {"id": "cloudformation", "name": "Cloudformation"}, {"id": "cloudwatch", "name": "Cloudwatch"}, {"id": "confluence", "name": "Confluence"}, {"id": "cursor", "name": "Cursor"}, {"id": "databricks", "name": "Databricks"}, {"id": "datadog", "name": "Datadog"}, {"id": "devin", "name": "Devin"}, {"id": "discord", "name": "Discord"}, {"id": "docusign", "name": "Docusign"}, {"id": "dropbox", "name": "Dropbox"}, {"id": "dspy", "name": "Dspy"}, {"id": "dub", "name": "Dub"}, {"id": "duckduckgo", "name": "Duckduckgo"}, {"id": "dynamodb", "name": "Dynamodb"}, {"id": "elasticsearch", "name": "Elasticsearch"}, {"id": "elevenlabs", "name": "Elevenlabs"}, {"id": "enrich", "name": "Enrich"}, {"id": "evernote", "name": "Evernote"}, {"id": "exa", "name": "Exa"}, {"id": "extend", "name": "Extend"}, {"id": "fathom", "name": "Fathom"}, {"id": "file", "name": "File"}, {"id": "firecrawl", "name": "Firecrawl"}, {"id": "fireflies", "name": "Fireflies"}, {"id": "function", "name": "Function"}, {"id": "gamma", "name": "Gamma"}, {"id": "gitlab", "name": "GitLab"}, {"id": "gong", "name": "Gong"}, {"id": "grafana", "name": "Grafana"}, {"id": "grain", "name": "Grain"}, {"id": "granola", "name": "Granola"}, {"id": "greenhouse", "name": "Greenhouse"}, {"id": "greptile", "name": "Greptile"}, {"id": "guardrails", "name": "Guardrails"}, {"id": "hex", "name": "Hex"}, {"id": "http", "name": "Http"}, {"id": "huggingface", "name": "Huggingface"}, {"id": "hunter", "name": "Hunter"}, {"id": "incidentio", "name": "Incidentio"}, {"id": "infisical", "name": "Infisical"}, {"id": "intercom", "name": "Intercom"}, {"id": "jina", "name": "Jina"}, {"id": "jsm", "name": "Jsm"}, {"id": "kalshi", "name": "Kalshi"}, {"id": "ketch", "name": "Ketch"}, {"id": "knowledge", "name": "Knowledge"}, {"id": "langsmith", "name": "Langsmith"}, {"id": "launchdarkly", "name": "Launchdarkly"}, {"id": "lemlist", "name": "Lemlist"}, {"id": "linkedin", "name": "Linkedin"}, {"id": "linkup", "name": "Linkup"}, {"id": "llm", "name": "Llm"}, {"id": "loops", "name": "Loops"}, {"id": "luma", "name": "Luma"}, {"id": "mailchimp", "name": "Mailchimp"}, {"id": "mailgun", "name": "Mailgun"}, {"id": "mem0", "name": "Mem0"}, {"id": "memory", "name": "Memory"}, {"id": "microsoft_ad", "name": "Microsoft Ad"}, {"id": "microsoft_dataverse", "name": "Microsoft Dataverse"}, {"id": "microsoft_excel", "name": "Microsoft Excel"}, {"id": "microsoft_planner", "name": "Microsoft Planner"}, {"id": "microsoft_teams", "name": "Microsoft Teams"}, {"id": "mistral", "name": "Mistral"}, {"id": "mongodb", "name": "Mongodb"}, {"id": "mysql", "name": "Mysql"}, {"id": "neo4j", "name": "Neo4J"}, {"id": "obsidian", "name": "Obsidian"}, {"id": "okta", "name": "Okta"}, {"id": "onedrive", "name": "Onedrive"}, {"id": "onepassword", "name": "Onepassword"}, {"id": "openai", "name": "Openai"}, {"id": "outlook", "name": "Outlook"}, {"id": "pagerduty", "name": "Pagerduty"}, {"id": "parallel", "name": "Parallel"}, {"id": "perplexity", "name": "Perplexity"}, {"id": "pinecone", "name": "Pinecone"}, {"id": "pipedrive", "name": "Pipedrive"}, {"id": "polymarket", "name": "Polymarket"}, {"id": "postgresql", "name": "Postgresql"}, {"id": "posthog", "name": "Posthog"}, {"id": "profound", "name": "Profound"}, {"id": "pulse", "name": "Pulse"}, {"id": "qdrant", "name": "Qdrant"}, {"id": "quiver", "name": "Quiver"}, {"id": "rds", "name": "Rds"}, {"id": "reddit", "name": "Reddit"}, {"id": "redis", "name": "Redis"}, {"id": "reducto", "name": "Reducto"}, {"id": "resend", "name": "Resend"}, {"id": "response", "name": "Response"}, {"id": "revenuecat", "name": "Revenuecat"}, {"id": "rippling", "name": "Rippling"}, {"id": "rootly", "name": "Rootly"}, {"id": "s3", "name": "S3"}, {"id": "search", "name": "Search"}, {"id": "secrets_manager", "name": "Secrets Manager"}, {"id": "sendgrid", "name": "Sendgrid"}, {"id": "sentry", "name": "Sentry"}, {"id": "serper", "name": "Serper"}, {"id": "servicenow", "name": "Servicenow"}, {"id": "sftp", "name": "Sftp"}, {"id": "shared", "name": "Shared"}, {"id": "sharepoint", "name": "Sharepoint"}, {"id": "shopify", "name": "Shopify"}, {"id": "similarweb", "name": "Similarweb"}, {"id": "sixtyfour", "name": "Sixtyfour"}, {"id": "sms", "name": "Sms"}, {"id": "smtp", "name": "Smtp"}, {"id": "spotify", "name": "Spotify"}, {"id": "sqs", "name": "Sqs"}, {"id": "ssh", "name": "Ssh"}, {"id": "stagehand", "name": "Stagehand"}, {"id": "stt", "name": "Stt"}, {"id": "supabase", "name": "Supabase"}, {"id": "table", "name": "Table"}, {"id": "tailscale", "name": "Tailscale"}, {"id": "tavily", "name": "Tavily"}, {"id": "telegram", "name": "Telegram"}, {"id": "textract", "name": "Textract"}, {"id": "thinking", "name": "Thinking"}, {"id": "tinybird", "name": "Tinybird"}, {"id": "trello", "name": "Trello"}, {"id": "tts", "name": "Tts"}, {"id": "twilio", "name": "Twilio"}, {"id": "twilio_voice", "name": "Twilio Voice"}, {"id": "typeform", "name": "Typeform"}, {"id": "upstash", "name": "Upstash"}, {"id": "vercel", "name": "Vercel"}, {"id": "video", "name": "Video"}, {"id": "vision", "name": "Vision"}, {"id": "wealthbox", "name": "Wealthbox"}, {"id": "webflow", "name": "Webflow"}, {"id": "whatsapp", "name": "Whatsapp"}, {"id": "wikipedia", "name": "Wikipedia"}, {"id": "wordpress", "name": "Wordpress"}, {"id": "workday", "name": "Workday"}, {"id": "workflow", "name": "Workflow"}, {"id": "x", "name": "X"}, {"id": "youtube", "name": "Youtube"}, {"id": "zendesk", "name": "Zendesk"}, {"id": "zep", "name": "Zep"}, {"id": "zoom", "name": "Zoom"}];

export function Integrations() {
  const { token, logout } = useAuth();
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

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
    setConnectError(null);
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

  const filteredComingSoon = COMING_SOON_INTEGRATIONS.filter(int => 
    int.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full overflow-y-auto bg-[#FAFAFA]">
      <div className="p-8 max-w-[1600px] mx-auto space-y-8 animate-in slide-in-from-bottom-4 duration-300">
        
        {/* Header & Search */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-border/50 pb-6">
          <div className="space-y-1.5">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Integrations</h1>
            <p className="text-sm text-muted-foreground">Connect external tools to give Katy the ability to execute work seamlessly.</p>
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
