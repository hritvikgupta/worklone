import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BookOpen, Search, Play, X, Plus, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  getPublicSkillDetail,
  listPublicSkills,
  createPublicSkill,
  type PublicSkillDetail,
  type PublicSkillListItem,
} from '@/lib/api';
import { useAuth } from '../contexts/AuthContext';

// Strip YAML-like frontmatter (name: ..., description: ...) from markdown content
function stripFrontmatter(markdown: string): string {
  return markdown
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim();
      if (trimmed === '') return true; // keep empty lines
      // Remove any line that starts with frontmatter keys
      if (/^(name|description|version|author|tags|category)\s*:/i.test(trimmed)) {
        return false;
      }
      return true;
    })
    .join('\n')
    .trim();
}

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('text-[34px] leading-[1.08] font-semibold tracking-tight text-foreground mb-7', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-9 mb-4 text-[24px] leading-tight font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-7 mb-3 text-[18px] leading-tight font-semibold text-foreground', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('mb-5 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('mb-5 list-disc space-y-2 pl-6 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('mb-5 list-decimal space-y-2 pl-6 text-[15px] leading-7 text-foreground', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className={cn('pl-1', className)} {...props} />
  ),
  hr: () => null,
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <code className={cn('rounded bg-muted px-1.5 py-0.5 text-[0.92em] text-foreground', className)} {...props} />
  ),
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className={cn('mb-6 overflow-x-auto rounded-xl border border-border bg-muted p-4 text-[13px] leading-6', className)} {...props} />
  ),
  strong: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <strong className={cn('font-semibold text-foreground', className)} {...props} />
  ),
  a: ({ className, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a className={cn('text-foreground underline decoration-zinc-300 underline-offset-4', className)} {...props} />
  ),
  table: ({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="mb-6 overflow-x-auto">
      <table className={cn('w-full border-collapse text-left text-[14px]', className)} {...props} />
    </div>
  ),
  th: ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className={cn('border-b border-border px-3 py-2 font-semibold text-foreground', className)} {...props} />
  ),
  td: ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className={cn('border-b border-border px-3 py-2 text-foreground', className)} {...props} />
  ),
};

export function SkillLibrary() {
  const { logout } = useAuth();
  const [query, setQuery] = useState('');
  const [skills, setSkills] = useState<PublicSkillListItem[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<PublicSkillListItem | null>(null);
  const [skillDetail, setSkillDetail] = useState<PublicSkillDetail | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creationModalOpen, setCreationModalOpen] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadSkills() {
      setIsLoadingList(true);
      setError(null);
      try {
        const data = await listPublicSkills();
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
        const detail = await getPublicSkillDetail(selectedSkill.slug);
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
      skill.title.toLowerCase().includes(normalized) ||
      skill.category.toLowerCase().includes(normalized) ||
      skill.employee_role.toLowerCase().includes(normalized)
    );
  }, [query, skills]);

  async function handleCreateSkill() {
    const title = createTitle.trim();
    const description = createDescription.trim();
    if (!title || !description || isCreating) return;

    setIsCreating(true);
    setError(null);
    try {
      await createPublicSkill({ title, description });
      setCreateTitle('');
      setCreateDescription('');
      setCreationModalOpen(false);
      // Reload the skills list
      const data = await listPublicSkills();
      setSkills(data);
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to create skill');
    } finally {
      setIsCreating(false);
    }
  }

  function handleCreationKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleCreateSkill();
    }
  }

  return (
    <div className="relative min-h-full">
      <div className="w-full space-y-8 pb-12">
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Skills</h2>
              <p className="text-muted-foreground text-sm leading-6">
                Worklone public workplace skills. These are reusable capability modules you can review and later assign during employee provisioning.
              </p>
            </div>
            <Button
              onClick={() => setCreationModalOpen(true)}
              className="gap-1.5 h-10 text-sm bg-primary text-primary-foreground hover:bg-primary/80"
            >
              <Plus className="h-4 w-4" />
              Create skill
            </Button>
          </div>

          <div className="relative max-w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search public skills..."
              className="pl-10 h-11 bg-secondary/20 border-border rounded-lg focus-visible:ring-primary/20 text-sm"
            />
          </div>
        </div>



        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : null}

        <div className="space-y-2">
          {isLoadingList ? (
            <div className="text-sm text-muted-foreground">Loading public skills...</div>
          ) : (
            filteredSkills.map((skill) => (
              <button
                key={skill.id}
                onClick={() => setSelectedSkill(skill)}
                className="w-full rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-muted"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-muted">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[15px] font-semibold text-foreground">{skill.title}</span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                        {skill.category}
                      </span>
                    </div>
                    <div className="mt-1 text-[13px] text-muted-foreground">
                      {skill.employee_role || 'General workplace'} · {skill.suggested_tools.length} suggested tools
                    </div>
                  </div>
                  <div className="text-muted-foreground">
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
            className="fixed inset-y-4 right-4 z-40 w-[min(560px,calc(100vw-2rem))] rounded-2xl border border-border bg-card shadow-2xl"
          >
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-5">
                  <div className="min-w-0">
                  <div className="truncate text-[14px] font-semibold text-foreground">{selectedSkill.title}</div>
                  <div className="text-[12px] text-muted-foreground">{selectedSkill.employee_role || selectedSkill.category}</div>
                  </div>
                  <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setSelectedSkill(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
                {isLoadingDetail || !skillDetail ? (
                  <div className="text-sm text-muted-foreground">Loading skill details...</div>
                ) : (
                  <div className="space-y-8">
                    <section className="space-y-3">
                      <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Overview</div>
                      <div className="rounded-xl border border-border bg-muted p-4 text-[14px] leading-6 text-foreground">
                        {skillDetail.description}
                      </div>
                    </section>

                    {skillDetail.skill_markdown ? (
                      <section>
                        <div className="mb-3 text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">SKILL.md</div>
                        <article className="prose prose-zinc max-w-none">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {stripFrontmatter(skillDetail.skill_markdown)}
                          </ReactMarkdown>
                        </article>
                      </section>
                    ) : null}

                    {skillDetail.notes ? (
                      <section className="space-y-3">
                        <div className="text-[12px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Notes</div>
                        <div className="rounded-xl border border-border bg-muted p-4 text-[14px] leading-6 text-foreground">
                          {skillDetail.notes}
                        </div>
                      </section>
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Create Skill Modal */}
      <AnimatePresence>
        {creationModalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => { if (!isCreating) setCreationModalOpen(false); }}
              className="fixed inset-0 z-50 bg-background/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-card p-6 shadow-2xl"
            >
              <div className="mb-5">
                <h3 className="text-sm font-semibold text-foreground">Create Public Skill</h3>
                <p className="text-[11px] text-muted-foreground">AI will generate a full SKILL.md for this capability</p>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">
                    Skill Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={createTitle}
                    onChange={(e) => setCreateTitle(e.target.value)}
                    placeholder="e.g. Inbox Triage and Action Routing"
                    disabled={isCreating}
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-foreground">
                    Description <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    value={createDescription}
                    onChange={(e) => setCreateDescription(e.target.value)}
                    placeholder="What should this skill do and when to use it..."
                    rows={4}
                    disabled={isCreating}
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
                  />
                </div>

                {error && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    {error}
                  </div>
                )}
              </div>

              <div className="mt-6 flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCreationModalOpen(false)}
                  disabled={isCreating}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleCreateSkill}
                  disabled={isCreating || !createTitle.trim() || !createDescription.trim()}
                  className="gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/80"
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      Create Skill
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
