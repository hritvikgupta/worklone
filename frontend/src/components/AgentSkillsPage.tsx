import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Search, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

type AgencySkill = {
  id: string;
  category: string;
  name: string;
  description: string;
  publisher: string;
  path: string;
};

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('mt-2 mb-5 text-3xl font-semibold tracking-tight text-zinc-900', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-9 mb-4 text-2xl font-semibold tracking-tight text-zinc-900', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-7 mb-3 text-xl font-semibold tracking-tight text-zinc-900', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('my-4 text-[16px] leading-8 text-zinc-700', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('my-5 list-disc space-y-2 pl-7 text-[16px] leading-8 text-zinc-700', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('my-5 list-decimal space-y-2 pl-7 text-[16px] leading-8 text-zinc-700', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className={cn('pl-1', className)} {...props} />
  ),
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <code className={cn('rounded bg-zinc-100 px-1.5 py-0.5 text-[0.9em] text-zinc-900', className)} {...props} />
  ),
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className={cn('my-6 overflow-x-auto rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-[13px] leading-6 text-zinc-800', className)} {...props} />
  ),
  strong: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <strong className={cn('font-semibold text-zinc-900', className)} {...props} />
  ),
  a: ({ className, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a className={cn('text-zinc-900 underline decoration-zinc-300 underline-offset-4', className)} {...props} />
  ),
};

export function AgentSkillsPage() {
  const [skills, setSkills] = useState<AgencySkill[]>([]);
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<AgencySkill | null>(null);
  const [selectedSkillMarkdown, setSelectedSkillMarkdown] = useState('');
  const [isLoadingSelectedSkill, setIsLoadingSelectedSkill] = useState(false);
  const [selectedSkillError, setSelectedSkillError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadSkills() {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/agency-skills.json');
        if (!response.ok) {
          throw new Error('Failed to load skills index');
        }
        const data = (await response.json()) as AgencySkill[];
        if (!cancelled) {
          setSkills(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load agent skills');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadSkills();

    return () => {
      cancelled = true;
    };
  }, []);

  const categories = useMemo(() => {
    const unique = Array.from(new Set(skills.map((skill) => skill.category))).sort();
    return ['All', ...unique];
  }, [skills]);

  const filteredSkills = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return skills.filter((skill) => {
      const matchesCategory = selectedCategory === 'All' || skill.category === selectedCategory;
      if (!matchesCategory) return false;
      if (!normalizedQuery) return true;

      return (
        skill.name.toLowerCase().includes(normalizedQuery) ||
        skill.category.toLowerCase().includes(normalizedQuery) ||
        skill.description.toLowerCase().includes(normalizedQuery)
      );
    });
  }, [skills, query, selectedCategory]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const skill of skills) {
      counts[skill.category] = (counts[skill.category] || 0) + 1;
    }
    return counts;
  }, [skills]);

  useEffect(() => {
    if (!selectedSkill) {
      setSelectedSkillMarkdown('');
      setSelectedSkillError(null);
      setIsLoadingSelectedSkill(false);
      return;
    }

    let cancelled = false;

    async function loadSkillMarkdown() {
      setIsLoadingSelectedSkill(true);
      setSelectedSkillError(null);
      try {
        const response = await fetch(selectedSkill.path);
        if (!response.ok) {
          throw new Error('Failed to load selected skill markdown');
        }
        const markdown = await response.text();
        if (!cancelled) {
          setSelectedSkillMarkdown(markdown);
        }
      } catch (err) {
        if (!cancelled) {
          setSelectedSkillError(err instanceof Error ? err.message : 'Unable to load selected skill');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSelectedSkill(false);
        }
      }
    }

    loadSkillMarkdown();
    return () => {
      cancelled = true;
    };
  }, [selectedSkill]);

  function stripFrontmatter(markdown: string) {
    if (!markdown.startsWith('---')) return markdown.trim();
    const stripped = markdown.replace(/^---\n[\s\S]*?\n---\n?/m, '');
    return stripped.trim();
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-zinc-900">
      <div className="fixed top-0 z-50 flex w-full justify-center border-b border-zinc-200/80 bg-white/95 backdrop-blur-md">
        <div className="flex w-full max-w-7xl items-center justify-between px-6 py-3 sm:px-8 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <img src="/brand/worklone-mark-black.png" alt="Worklone" className="h-7 w-auto" />
            <div className="text-[18px] tracking-[-0.02em] text-zinc-900 font-['Lato']">Worklone</div>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <Link to="/what-is-worklone" className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950">
              What is Worklone
            </Link>
            <Link to="/agentskills" className="text-sm font-semibold text-zinc-950">
              Agent Skills
            </Link>
            <Link to="/documentation" className="text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950">
              Documentation
            </Link>
          </div>

          <Link
            to="/waitlist"
            className="inline-flex items-center gap-2 rounded-md bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
          >
            Join Waitlist
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      <section className="mx-auto max-w-7xl px-6 pb-10 pt-28 sm:px-8 lg:px-10">
        <div
          className="overflow-hidden rounded-2xl border border-zinc-200 bg-white"
          style={{
            backgroundImage:
              'repeating-linear-gradient(to bottom, rgba(15,23,42,0.03), rgba(15,23,42,0.03) 1px, transparent 1px, transparent 12px)',
          }}
        >
          <div className="grid gap-0 lg:grid-cols-[1.7fr_1fr]">
            <div className="border-b border-zinc-200 p-8 lg:border-b-0 lg:border-r">
              <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">WORKLONE</div>
              <h1 className="mt-6 text-5xl font-medium leading-[1.1] tracking-tight text-zinc-900">Worklone Agent Skills</h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-zinc-600">
                Skills available inside Worklone, sourced from your cloned agency-agents repository.
              </p>
            </div>

            <div className="border-b border-zinc-200 p-8 lg:border-b-0 lg:border-r">
              <div className="text-xs uppercase tracking-[0.22em] text-zinc-500">Quick Stats</div>
              <div className="mt-6 space-y-4 text-sm">
                <div className="flex items-center justify-between border-b border-zinc-200 pb-3">
                  <span className="text-zinc-500">Last Updated</span>
                  <span className="font-semibold text-zinc-900">Apr 21, 2026</span>
                </div>
                <div className="flex items-center justify-between border-b border-zinc-200 pb-3">
                  <span className="text-zinc-500">Categories</span>
                  <span className="font-semibold text-zinc-900">{categories.length - 1}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-zinc-500">Official Skills</span>
                  <span className="font-semibold text-zinc-900">{skills.length}</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-16 sm:px-8 lg:px-10">
        <div className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8">
          <div className="mb-6">
            <h2 className="text-3xl font-medium tracking-tight text-zinc-900">Find Skills</h2>
            <p className="mt-2 text-zinc-600">Browse categories and search across the cloned agency-agents repository.</p>
          </div>

          <div className="relative mb-6">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search all skills"
              className="h-11 w-full rounded-md border border-zinc-200 bg-white pl-10 pr-4 text-sm text-zinc-900 outline-none transition focus:border-zinc-400"
            />
          </div>

          <div className="mb-8 flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={[
                  'rounded-full border px-3 py-1.5 text-xs font-medium transition',
                  selectedCategory === category
                    ? 'border-zinc-900 bg-zinc-900 text-white'
                    : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:text-zinc-900',
                ].join(' ')}
              >
                {category}
                {category !== 'All' ? ` ${categoryCounts[category] || 0}` : ` ${skills.length}`}
              </button>
            ))}
          </div>

          {isLoading ? <div className="text-sm text-zinc-500">Loading skills...</div> : null}
          {error ? <div className="text-sm text-red-600">{error}</div> : null}

          {!isLoading && !error ? (
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {filteredSkills.map((skill) => (
                <button
                  key={skill.id}
                  onClick={() => setSelectedSkill(skill)}
                  className="group rounded-xl border border-zinc-200 bg-white p-4 transition hover:-translate-y-0.5 hover:border-zinc-300 hover:shadow-sm"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2 py-0.5 text-[11px] uppercase tracking-wide text-zinc-600">
                      {skill.category}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-zinc-900">{skill.name}</h3>
                  <p className="mt-2 text-xs leading-5 text-zinc-600">
                    {skill.description || 'No description provided in frontmatter.'}
                  </p>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      {selectedSkill ? (
        <div className="fixed inset-0 z-[70] bg-zinc-900/30 p-4 backdrop-blur-[2px] sm:p-8" onClick={() => setSelectedSkill(null)}>
          <div
            className="mx-auto flex h-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-zinc-200 px-5 py-4">
              <div className="min-w-0">
                <div className="text-xs uppercase tracking-[0.16em] text-zinc-500">{selectedSkill.category}</div>
                <h3 className="mt-1 truncate text-lg font-semibold text-zinc-900">{selectedSkill.name}</h3>
              </div>
              <button
                onClick={() => setSelectedSkill(null)}
                className="rounded-md p-1.5 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-800"
                aria-label="Close skill modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
              {isLoadingSelectedSkill ? <div className="text-sm text-zinc-500">Loading skill...</div> : null}
              {selectedSkillError ? <div className="text-sm text-red-600">{selectedSkillError}</div> : null}
              {!isLoadingSelectedSkill && !selectedSkillError ? (
                <article className="mx-auto w-full max-w-4xl">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {stripFrontmatter(selectedSkillMarkdown)}
                  </ReactMarkdown>
                </article>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
