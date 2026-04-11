import { createClient } from '@libsql/client';

type WaitlistPayload = {
  email?: string;
  name?: string;
  company?: string;
  source?: string;
};

type VercelRequest = {
  method?: string;
  body?: WaitlistPayload | string;
};

type VercelResponse = {
  status: (code: number) => VercelResponse;
  json: (body: unknown) => void;
  setHeader: (name: string, value: string) => void;
};

const TURSO_DATABASE_URL = process.env.TURSO_DATABASE_URL;
const TURSO_AUTH_TOKEN = process.env.TURSO_AUTH_TOKEN;

function getClient() {
  if (!TURSO_DATABASE_URL || !TURSO_AUTH_TOKEN) {
    throw new Error('Missing Turso environment variables.');
  }

  return createClient({
    url: TURSO_DATABASE_URL,
    authToken: TURSO_AUTH_TOKEN,
  });
}

function parseBody(body: VercelRequest['body']): WaitlistPayload {
  if (!body) return {};
  if (typeof body === 'string') {
    try {
      return JSON.parse(body) as WaitlistPayload;
    } catch {
      return {};
    }
  }
  return body;
}

function normalizeText(value?: string) {
  return value?.trim() || null;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  res.setHeader('Content-Type', 'application/json');

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  const { email, name, company, source } = parseBody(req.body);
  const normalizedEmail = email?.trim().toLowerCase();

  if (!normalizedEmail) {
    return res.status(400).json({ error: 'Email is required.' });
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(normalizedEmail)) {
    return res.status(400).json({ error: 'Please enter a valid email.' });
  }

  try {
    const client = getClient();

    await client.execute(`
      CREATE TABLE IF NOT EXISTS waitlist_signups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        name TEXT,
        company TEXT,
        source TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await client.execute({
      sql: `
        INSERT INTO waitlist_signups (email, name, company, source)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
          name = COALESCE(excluded.name, waitlist_signups.name),
          company = COALESCE(excluded.company, waitlist_signups.company),
          source = COALESCE(excluded.source, waitlist_signups.source)
      `,
      args: [
        normalizedEmail,
        normalizeText(name),
        normalizeText(company),
        normalizeText(source) || 'landing_page',
      ],
    });

    return res.status(200).json({
      success: true,
      message: 'You are on the waitlist.',
    });
  } catch (error) {
    console.error('Waitlist signup failed:', error);
    return res.status(500).json({
      error: 'Unable to record your email right now.',
    });
  }
}
