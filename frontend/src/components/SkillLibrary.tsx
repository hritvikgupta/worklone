import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BookOpen, Search, Play, X, Pencil, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  getVercelSkillDetail,
  listVercelSkills,
  type VercelSkillDetail,
  type VercelSkillListItem,
} from '@/lib/api';
import { useAuth } from '../contexts/AuthContext';

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('text-[34px] leading-[1.08] font-semibold tracking-tight text-zinc-950 mb-7', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-9 mb-4 text-[24px] leading-tight font-semibold tracking-tight text-zinc-950', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-7 mb-3 text-[18px] leading-tight font-semibold text-zinc-900', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('mb-5 text-[15px] leading-7 text-zinc-700', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('mb-5 list-disc space-y-2 pl-6 text-[15px] leading-7 text-zinc-700', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('mb-5 list-decimal space-y-2 pl-6 text-[15px] leading-7 text-zinc-700', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className={cn('pl-1', className)} {...props} />
  ),
  hr: (props: React.HTMLAttributes<HTMLHRElement>) => <hr className="my-8 border-zinc-200" {...props} />,
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <code className={cn('rounded bg-zinc-100 px-1.5 py-0.5 text-[0.92em] text-zinc-900', className)} {...props} />
  ),
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className={cn('mb-6 overflow-x-auto rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-[13px] leading-6', className)} {...props} />
  ),
  strong: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <strong className={cn('font-semibold text-zinc-950', className)} {...props} />
  ),
  a: ({ className, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a className={cn('text-zinc-900 underline decoration-zinc-300 underline-offset-4', className)} {...props} />
  ),
  table: ({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="mb-6 overflow-x-auto">
      <table className={cn('w-full border-collapse text-left text-[14px]', className)} {...props} />
    </div>
  ),
  th: ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className={cn('border-b border-zinc-200 px-3 py-2 font-semibold text-zinc-900', className)} {...props} />
  ),
  td: ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className={cn('border-b border-zinc-100 px-3 py-2 text-zinc-700', className)} {...props} />
  ),
};

function htmlToMarkdown(htmlString: string): string {
  return htmlString
    .replace(/<h1[^>]*>(.*?)<\/h1>/gis, '# $1\n\n')
    .replace(/<h2[^>]*>(.*?)<\/h2>/gis, '## $1\n\n')
    .replace(/<h3[^>]*>(.*?)<\/h3>/gis, '### $1\n\n')
    .replace(/<strong[^>]*>(.*?)<\/strong>/gis, '**$1**')
    .replace(/<code[^>]*>(.*?)<\/code>/gis, (_, inner) => `\`${inner.replace(/<[^>]+>/g, '').trim()}\``)
    .replace(/<li[^>]*>(.*?)<\/li>/gis, (_, inner) => `- ${inner.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()}\n`)
    .replace(/<ul[^>]*>/gis, '\n')
    .replace(/<\/ul>/gis, '\n')
    .replace(/<ol[^>]*>/gis, '\n')
    .replace(/<\/ol>/gis, '\n')
    .replace(/<p[^>]*>(.*?)<\/p>/gis, (_, inner) => `${inner.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()}\n\n`)
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function trustTone(value: string) {
  const normalized = value.toLowerCase();
  if (normalized.includes('pass')) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
  if (normalized.includes('warn')) return 'text-amber-700 bg-amber-50 border-amber-200';
  return 'text-zinc-600 bg-zinc-50 border-zinc-200';
}

export function SkillLibrary() {
  const { logout } = useAuth();
  const [query, setQuery] = useState('');
  const [skills, setSkills] = useState<VercelSkillListItem[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<VercelSkillListItem | null>(null);
  const [skillDetail, setSkillDetail] = useState<VercelSkillDetail | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSkills() {
      setIsLoadingList(true);
      setError(null);
      try {
        const data = await listVercelSkills();
        if (!cancelled) {
          setSkills(data);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load skills');
      } finally {
        if (!cancelled) {
          setIsLoadingList(false);
        }
      }
    }

    loadSkills();
    return () => {
      cancelled = true;
    };
  }, [logout]);

  useEffect(() => {
    if (!selectedSkill) {
      setSkillDetail(null);
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      setIsLoadingDetail(true);
      setError(null);
      try {
        const detail = await getVercelSkillDetail(selectedSkill.source, selectedSkill.name);
        if (!cancelled) {
          setSkillDetail(detail);
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load skill detail');
      } finally {
        if (!cancelled) {
          setIsLoadingDetail(false);
        }
      }
    }

    loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedSkill, logout]);

  const filteredSkills = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return skills;
    return skills.filter((skill) =>
      skill.name.toLowerCase().includes(normalized) ||
      skill.source.toLowerCase().includes(normalized)
    );
  }, [query, skills]);

  const hasMetadata = Boolean(
    skillDetail &&
      (skillDetail.repository || skillDetail.weekly_installs || skillDetail.github_stars || skillDetail.first_seen)
  );

  const trustEntries = skillDetail
    ? Object.entries(skillDetail.trust).filter(([, value]) => value)
    : [];

  return (
    <div className="relative min-h-full">
      <div className="w-full space-y-8 pb-12">
        <div className="space-y-3">
          <h2 className="text-2xl font-semibold tracking-tight">Skills</h2>
          <p className="text-muted-foreground text-sm leading-6">
            Imported from Vercel&apos;s `skills.sh` catalog. Click a skill to inspect its install command and `SKILL.md`.
          </p>

          <div className="relative max-w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search Vercel skills..."
              className="pl-10 h-11 bg-secondary/20 border-border/40 rounded-lg focus-visible:ring-primary/20 text-sm"
            />
          </div>
        </div>

        <div className="flex items-center gap-6 text-sm text-muted-foreground">
          <div><span className="font-semibold text-zinc-900">{skills.length}</span> skills</div>
          <div><span className="font-semibold text-zinc-900">18</span> sources</div>
          <div><span className="font-semibold text-zinc-900">skills.sh/vercel</span> catalog</div>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : null}

        <div className="space-y-2">
          {isLoadingList ? (
            <div className="text-sm text-muted-foreground">Loading Vercel skills...</div>
          ) : (
            filteredSkills.map((skill) => (
              <button
                key={skill.id}
                onClick={() => setSelectedSkill(skill)}
                className="w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-left transition-colors hover:bg-zinc-50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-50">
                    <BookOpen className="h-4 w-4 text-zinc-600" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[15px] font-semibold text-zinc-900">{skill.name}</span>
                      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-500">
                        {skill.source}
                      </span>
                    </div>
                    <div className="mt-1 text-[13px] text-zinc-500">
                      Vercel source: {skill.source} · {skill.installs_label} installs
                    </div>
                  </div>
                  <div className="text-zinc-400">
                    <Play className="h-4 w-4" />
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <AnimatePresence>
        {selectedSkill && (
          <motion.aside
            initial={{ x: 32, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 32, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 340, damping: 30 }}
            className="fixed inset-y-4 right-4 z-40 w-[min(560px,calc(100vw-2rem))] rounded-2xl border border-zinc-200 bg-white shadow-2xl"
          >
            <div className="flex h-full min-h-0 flex-col">
              <div className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 px-5">
                <div className="min-w-0">
                  <div className="truncate text-[14px] font-semibold text-zinc-900">{selectedSkill.name}</div>
                  <div className="text-[12px] text-zinc-500">{selectedSkill.source}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" className="h-8 gap-1 text-[12px]">
                    <Play className="h-3.5 w-3.5" />
                    Run
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedSkill(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
                {isLoadingDetail || !skillDetail ? (
                  <div className="text-sm text-muted-foreground">Loading skill details...</div>
                ) : (
                  <div className="space-y-8 pb-24">
                    <div>
                      <div className="mb-2 text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Install</div>
                      <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3 font-mono text-[13px] text-zinc-700">
                        {skillDetail.install_command}
                      </div>
                    </div>

                    {skillDetail.summary_html ? (
                      <section>
                        <div className="mb-3 text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Summary</div>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {htmlToMarkdown(skillDetail.summary_html)}
                        </ReactMarkdown>
                      </section>
                    ) : null}

                    {skillDetail.skill_html ? (
                      <section>
                        <div className="mb-3 text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">SKILL.md</div>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                          {htmlToMarkdown(skillDetail.skill_html)}
                        </ReactMarkdown>
                      </section>
                    ) : null}

                    {hasMetadata ? (
                      <section className="space-y-3">
                        <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Metadata</div>
                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                          {skillDetail.repository ? (
                            <div className="rounded-xl border border-zinc-200 p-4">
                              <div className="text-[12px] text-zinc-500">Repository</div>
                              <div className="mt-1 text-[14px] font-medium text-zinc-900">{skillDetail.repository}</div>
                            </div>
                          ) : null}
                          {skillDetail.weekly_installs ? (
                            <div className="rounded-xl border border-zinc-200 p-4">
                              <div className="text-[12px] text-zinc-500">Weekly installs</div>
                              <div className="mt-1 text-[14px] font-medium text-zinc-900">{skillDetail.weekly_installs}</div>
                            </div>
                          ) : null}
                          {skillDetail.github_stars ? (
                            <div className="rounded-xl border border-zinc-200 p-4">
                              <div className="text-[12px] text-zinc-500">GitHub stars</div>
                              <div className="mt-1 text-[14px] font-medium text-zinc-900">{skillDetail.github_stars}</div>
                            </div>
                          ) : null}
                          {skillDetail.first_seen ? (
                            <div className="rounded-xl border border-zinc-200 p-4">
                              <div className="text-[12px] text-zinc-500">First seen</div>
                              <div className="mt-1 text-[14px] font-medium text-zinc-900">{skillDetail.first_seen}</div>
                            </div>
                          ) : null}
                        </div>
                      </section>
                    ) : null}

                    {trustEntries.length > 0 ? (
                      <section className="space-y-3">
                        <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-zinc-400">Trust</div>
                        <div className="flex flex-wrap gap-2">
                          {trustEntries.map(([label, value]) => (
                            <span
                              key={label}
                              className={`rounded-full border px-3 py-1 text-[12px] font-medium ${trustTone(value)}`}
                            >
                              {label.replace('_', ' ')}: {value}
                            </span>
                          ))}
                        </div>
                      </section>
                    ) : null}
                  </div>
                )}
              </div>

              <div className="sticky bottom-0 shrink-0 border-t border-zinc-200 bg-white px-5 py-4">
                <div className="grid grid-cols-2 gap-3">
                  <Button variant="outline" className="h-10 gap-2 text-[13px]">
                    <Pencil className="h-4 w-4" />
                    Edit
                  </Button>
                  <Button variant="outline" className="h-10 gap-2 text-[13px] text-red-600 border-red-200 hover:bg-red-50">
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}
