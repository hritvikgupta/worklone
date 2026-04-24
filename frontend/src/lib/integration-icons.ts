export const INTEGRATION_ICON_ALIASES: Record<string, string> = {
  googlecalendar: 'google_calendar',
  googledrive: 'google_drive',
  googlecalendartool: 'google_calendar',
  googledrivetool: 'google_drive',
  postgresqltool: 'postgresql',
  pager_duty: 'pagerduty',
  pagerdutytool: 'pagerduty',
  boxsigntool: 'box_sign',
  twiliosms: 'sms',
  fal: 'video',
  fal_ai: 'video',
};

export const SIMPLE_ICON_OVERRIDES: Record<string, string> = {
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

export function normalizeIntegrationId(raw: string): string {
  const value = (raw || '')
    .replace(/tool$/i, '')
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/[-\s]+/g, '_')
    .replace(/__+/g, '_')
    .toLowerCase()
    .trim();

  return INTEGRATION_ICON_ALIASES[value] || value;
}

function toSimpleIconsUrl(id: string): string {
  const override = SIMPLE_ICON_OVERRIDES[id];
  if (override) {
    return override.startsWith('/') ? override : `https://cdn.simpleicons.org/${override}`;
  }
  return `https://cdn.simpleicons.org/${id.replace(/_/g, '')}/71717A`;
}

export function getIntegrationIconSources(id: string): string[] {
  const normalized = normalizeIntegrationId(id);
  const dashed = normalized.replace(/_/g, '-');

  return [
    `/integrations/icons/${normalized}.svg`,
    `/integrations/icons/${normalized}.png`,
    `/integrations/icons/${dashed}.svg`,
    `/integrations/icons/${dashed}.png`,
    `/icons/${normalized}.svg`,
    `/icons/${dashed}.svg`,
    toSimpleIconsUrl(normalized),
  ];
}

export function integrationInitials(name: string): string {
  const clean = (name || '').trim();
  if (!clean) return '??';
  return clean
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('');
}
