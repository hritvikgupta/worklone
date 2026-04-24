import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';
import {
  integrationInitials,
  normalizeIntegrationId,
} from '@/src/lib/integration-icons';
import { SIM_ICON_COMPONENT_BY_INTEGRATION_KEY } from '@/src/lib/sim-icon-map';
import { SIM_INTEGRATIONS_BY_TYPE, SIM_TYPE_BY_ALIAS } from '@/src/lib/sim-integrations-map';
import * as SimReferenceIcons from '@/src/components/SimReferenceIcons';

type ToolLike = {
  name?: string;
  runtime_name?: string;
};

const COMPOUND_PREFIXES = ['google', 'microsoft', 'box', 'twilio', 'box_sign'];

// Explicit overrides: tool name prefix → integration provider id
const TOOL_TO_PROVIDER: Record<string, string> = {
  gmail: 'google',
  google: 'google',
  slack: 'slack',
  notion: 'notion',
  github: 'github',
  jira: 'jira',
  salesforce: 'salesforce',
  linear: 'linear',
  hubspot: 'hubspot',
  stripe: 'stripe',
  airtable: 'airtable',
  asana: 'asana',
  attio: 'attio',
  box: 'box',
  calcom: 'calcom',
  confluence: 'confluence',
  docusign: 'docusign',
  dropbox: 'dropbox',
  pipedrive: 'pipedrive',
  reddit: 'reddit',
  shopify: 'shopify',
  webflow: 'webflow',
  wordpress: 'wordpress',
  zoom: 'zoom',
  agentmail: 'agentmail',
  ahrefs: 'ahrefs',
  airweave: 'airweave',
  apollo: 'apollo',
  ashby: 'ashby',
  cursor: 'cursor',
  datadog: 'datadog',
  devin: 'devin',
  discord: 'discord',
  evernote: 'evernote',
  exa: 'exa',
  extend: 'extend',
  firecrawl: 'firecrawl',
  gamma: 'gamma',
  gitlab: 'gitlab',
  gong: 'gong',
  granola: 'granola',
  greenhouse: 'greenhouse',
  hex: 'hex',
  hunter: 'hunter',
  incidentio: 'incidentio',
  intercom: 'intercom',
  kalshi: 'kalshi',
  langsmith: 'langsmith',
  loops: 'loops',
  luma: 'luma',
  pagerduty: 'pagerduty',
  reducto: 'reducto',
  sixtyfour: 'sixtyfour',
  trello: 'trello',
  vercel: 'vercel',
  youtube: 'youtube',
  zendesk: 'zendesk',
  zep: 'zep',
  cloudwatch: 'aws',
  s3: 'aws',
  neo4j: 'neo4j',
  postgresql: 'postgresql',
  redis: 'redis',
  databricks: 'databricks',
  workday: 'workday',
  video: 'video',
  sms: 'sms',
  x: 'x',
  twitter: 'x',
  outlook: 'outlook',
};

export function resolveIntegrationIdFromTool(tool: ToolLike): string {
  const runtime = normalizeIntegrationId(tool.runtime_name || '');
  const name = normalizeIntegrationId(tool.name || '');
  const candidate = runtime || name;
  if (!candidate) return '';

  // Check explicit override first
  const parts = candidate.split('_').filter(Boolean);
  const first = parts[0];
  if (TOOL_TO_PROVIDER[candidate]) return TOOL_TO_PROVIDER[candidate];
  if (TOOL_TO_PROVIDER[first]) return TOOL_TO_PROVIDER[first];

  if (parts.length <= 1) return candidate;
  if (COMPOUND_PREFIXES.includes(first) && parts.length >= 2) {
    return `${first}_${parts[1]}`;
  }
  return first;
}

export function IntegrationIcon({
  id,
  name,
  className,
}: {
  id: string;
  name: string;
  className?: string;
}) {
  const resolved = useMemo(() => resolveSimIntegration(id, name), [id, name]);
  const SimIconComponent = useMemo(() => {
    if (!resolved) return null;
    const componentName = SIM_ICON_COMPONENT_BY_INTEGRATION_KEY[resolved.type];
    if (!componentName) return null;
    return (SimReferenceIcons as Record<string, React.ComponentType<any>>)[componentName] || null;
  }, [resolved]);

  if (SimIconComponent && resolved) {
    return (
      <div
        className={cn('flex items-center justify-center rounded-md border border-border', className)}
        style={{ background: resolved.bgColor }}
      >
        <SimIconComponent className="h-[80%] w-[80%] text-white" />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-md border border-border bg-muted text-[10px] font-semibold text-muted-foreground',
        className
      )}
    >
      {integrationInitials(name)}
    </div>
  );
}

function resolveSimIntegration(id: string, name: string): { type: string; bgColor: string } | null {
  const normalized = normalizeIntegrationId(id);
  const lowerName = (name || '').toLowerCase();
  const normalizedName = normalizeIntegrationId(name);
  const normalizedCompact = normalized.replace(/_/g, '');

  const candidates = [
    normalized,
    normalizedCompact,
    normalizedName,
    normalizedName.replace(/_/g, ''),
  ];

  if (normalized === 'google') {
    if (lowerName.includes('gmail')) candidates.push('gmail');
    if (lowerName.includes('calendar')) candidates.push('google_calendar');
    if (lowerName.includes('drive')) candidates.push('google_drive');
    if (lowerName.includes('docs')) candidates.push('google_docs');
    if (lowerName.includes('sheets')) candidates.push('google_sheets');
    if (lowerName.includes('slides')) candidates.push('google_slides');
    if (lowerName.includes('forms')) candidates.push('google_forms');
    if (lowerName.includes('meet')) candidates.push('google_meet');
    if (lowerName.includes('tasks')) candidates.push('google_tasks');
    if (lowerName.includes('ads')) candidates.push('google_ads');
    if (lowerName.includes('bigquery')) candidates.push('google_bigquery');
  }

  for (const candidate of candidates) {
    const simType = SIM_TYPE_BY_ALIAS[candidate];
    if (!simType) continue;
    if (!SIM_ICON_COMPONENT_BY_INTEGRATION_KEY[simType]) continue;
    const meta = SIM_INTEGRATIONS_BY_TYPE[simType];
    if (!meta) continue;
    return { type: simType, bgColor: meta.bgColor };
  }
  return null;
}
