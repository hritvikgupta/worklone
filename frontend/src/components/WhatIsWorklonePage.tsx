import React, { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ChevronDown, BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { researchArticles } from './ResearchArticlePage';

type ParsedSection = {
  title: string;
  body: string;
};

function parseArticle(markdown: string) {
  const lines = markdown.replace(/\r/g, '').split('\n');

  let title = 'What is Worklone?';
  let subtitle = 'The operating system for specialized AI employees.';
  let i = 0;

  while (i < lines.length && !lines[i].trim().startsWith('# ')) i += 1;
  if (i < lines.length) {
    title = lines[i].trim().replace(/^#\s+/, '');
    i += 1;
  }

  while (i < lines.length && !lines[i].trim()) i += 1;
  if (i < lines.length && lines[i].trim().startsWith('> ')) {
    subtitle = lines[i].trim().replace(/^>\s+/, '');
    i += 1;
  }

  const remaining = lines.slice(i);
  const intro: string[] = [];
  const sections: ParsedSection[] = [];

  let cursor = 0;
  while (cursor < remaining.length) {
    const line = remaining[cursor].trim();
    if (!line || line === '---') {
      cursor += 1;
      continue;
    }
    if (line.startsWith('## ')) break;
    intro.push(remaining[cursor]);
    cursor += 1;
  }

  while (cursor < remaining.length) {
    const line = remaining[cursor].trim();
    if (!line || line === '---') {
      cursor += 1;
      continue;
    }
    if (!line.startsWith('## ')) {
      cursor += 1;
      continue;
    }

    const sectionTitle = line.replace(/^##\s+/, '').trim();
    cursor += 1;
    const body: string[] = [];

    while (cursor < remaining.length) {
      const next = remaining[cursor].trim();
      if (next.startsWith('## ')) break;
      if (next === '---') {
        cursor += 1;
        continue;
      }
      body.push(remaining[cursor]);
      cursor += 1;
    }

    sections.push({
      title: sectionTitle,
      body: body.join('\n').trim(),
    });
  }

  return {
    title,
    subtitle,
    intro: intro.join('\n').trim(),
    sections,
  };
}

function SiteFooter() {
  return (
    <footer className="relative overflow-hidden bg-[#111111] px-6 py-14 text-white sm:px-8 lg:px-10">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.07),transparent_35%),radial-gradient(circle_at_top_right,rgba(255,255,255,0.05),transparent_25%),linear-gradient(180deg,rgba(255,255,255,0.03),rgba(0,0,0,0.08)),linear-gradient(135deg,#171717_0%,#111111_28%,#1a1a1a_50%,#0f0f0f_72%,#171717_100%)]" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-[linear-gradient(180deg,transparent,rgba(0,0,0,0.22))]" />
      <div className="relative mx-auto max-w-6xl">
        <div className="grid gap-10 border-b border-white/10 pb-12 md:grid-cols-2 lg:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,1fr))] lg:gap-12">
          <div className="max-w-sm">
            <div className="flex items-center gap-3">
              <img src="/brand/worklone-mark-white.png" alt="Worklone" className="h-7 w-auto" />
              <div className="text-lg font-semibold tracking-tight text-white">Worklone</div>
            </div>
            <p className="mt-4 text-sm leading-6 text-white/64">
              The operating system for AI employees across planning, execution, files, workflows, and integrations.
            </p>
          </div>

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Company</div>
            <div className="mt-4 space-y-2.5 text-base text-white/72">
              <Link to="/privacy-policy" className="block transition-colors hover:text-white">
                Privacy Policy
              </Link>
              <Link to="/contact" className="block transition-colors hover:text-white">
                Contact
              </Link>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Research</div>
            <div className="mt-4 space-y-2.5 text-base text-white/72">
              {researchArticles.map((article) => (
                <Link 
                  key={article.slug} 
                  to={`/research/${article.slug}`} 
                  className="block transition-colors hover:text-white"
                >
                  {article.title}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Company</div>
            <div className="mt-4 space-y-2.5 text-base text-white/72">
              <Link to="/privacy-policy" className="block transition-colors hover:text-white">
                Privacy Policy
              </Link>
              <Link to="/contact" className="block transition-colors hover:text-white">
                Contact
              </Link>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/88">Connect</div>
            <div className="mt-4 space-y-2.5 text-base text-white/72">
              <a
                href="https://x.com/worklonemployee"
                target="_blank"
                rel="noreferrer"
                className="block transition-colors hover:text-white"
              >
                Twitter
              </a>
              <span className="block">LinkedIn</span>
              <span className="block">GitHub</span>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-4 text-xs text-white/58 md:flex-row md:items-center md:justify-between">
          <span>© 2026 Worklone. All rights reserved.</span>
          <div className="flex flex-wrap items-center gap-4 md:justify-end md:gap-6">
            <span>Privacy Policy</span>
            <span>Terms</span>
            <span>Contact</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

function EditorialMarkdown({
  content,
  compact = false,
}: {
  content: string;
  compact?: boolean;
}) {
  const components = {
    h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
      <h3
        className={cn(
          compact
            ? 'mt-7 mb-2 text-[17px] leading-tight font-semibold text-zinc-900'
            : 'mt-8 mb-3 text-[18px] leading-tight font-semibold text-zinc-900',
          className
        )}
        {...props}
      />
    ),
    p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
      <p
        className={cn(
          compact
            ? 'mb-4 text-[15px] leading-7 text-zinc-700'
            : 'mb-5 text-[15px] leading-7 text-zinc-700 sm:text-[16px] sm:leading-8',
          className
        )}
        {...props}
      />
    ),
    strong: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
      <strong className={cn('font-semibold text-zinc-950', className)} {...props} />
    ),
    ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
      <ul className={cn('mb-6 space-y-3 pl-0 text-[15px] leading-7 text-zinc-700', className)} {...props} />
    ),
    ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
      <ol className={cn('mb-6 list-decimal space-y-3 pl-5 text-[15px] leading-7 text-zinc-700', className)} {...props} />
    ),
    li: ({ className, children, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
      <li className={cn('flex items-start gap-3', className)} {...props}>
        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-zinc-900" />
        <span>{children}</span>
      </li>
    ),
    img: ({ src, alt }: { src?: string; alt?: string }) => (
      <div className="my-8 overflow-hidden rounded-[20px] bg-[#f5f2eb]">
        <img
          src={src}
          alt={alt || ''}
          className="mx-auto max-h-[520px] w-auto object-contain"
        />
      </div>
    ),
    table: ({ className, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
      <div className="my-8 overflow-x-auto rounded-[18px] border border-zinc-200 bg-white">
        <table className={cn('w-full border-collapse text-left text-[14px]', className)} {...props} />
      </div>
    ),
    th: ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
      <th className={cn('border-b border-zinc-200 bg-zinc-50 px-4 py-3 font-semibold text-zinc-900', className)} {...props} />
    ),
    td: ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
      <td className={cn('border-b border-zinc-100 px-4 py-3 text-zinc-700', className)} {...props} />
    ),
    code: ({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) => {
      const isInline = !String(className || '').includes('language-');
      if (isInline) {
        return (
          <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-[0.92em] text-zinc-900" {...props}>
            {children}
          </code>
        );
      }
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    pre: ({ children }: React.HTMLAttributes<HTMLPreElement>) => {
      const child = React.Children.toArray(children)[0] as React.ReactElement<{ children?: React.ReactNode }>;
      const raw = typeof child?.props?.children === 'string' ? child.props.children.trim() : '';
      const isFlow = raw.includes('→');

      if (isFlow) {
        const steps = raw
          .split('→')
          .map((item) => item.trim())
          .filter(Boolean);

        return (
          <div className="my-8 rounded-[22px] border border-zinc-200 bg-[#faf8f4] p-5">
            <div className="grid gap-3 sm:grid-cols-[repeat(auto-fit,minmax(120px,1fr))]">
              {steps.map((step, index) => (
                <div key={`${step}-${index}`} className="relative">
                  <div className="rounded-2xl border border-zinc-200 bg-white px-4 py-4 text-center text-sm font-medium text-zinc-900 shadow-[0_8px_20px_rgba(27,31,35,0.04)]">
                    {step}
                  </div>
                  {index < steps.length - 1 ? (
                    <div className="hidden sm:block absolute left-[calc(100%+4px)] top-1/2 w-3 -translate-y-1/2 text-zinc-300">
                      →
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        );
      }

      return (
        <pre className="my-8 overflow-x-auto rounded-[18px] border border-zinc-200 bg-zinc-50 p-5 text-[13px] leading-6 text-zinc-800">
          {children}
        </pre>
      );
    },
    a: ({ className, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
      <a
        className={cn('font-medium text-zinc-900 underline decoration-zinc-300 underline-offset-4 hover:text-zinc-700', className)}
        {...props}
      />
    ),
  };

  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{content}</ReactMarkdown>;
}

export function WhatIsWorklonePage() {
  const [markdownContent, setMarkdownContent] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/what-is-worklone.md')
      .then((res) => res.text())
      .then((text) => {
        setMarkdownContent(text);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load README:', err);
        setLoading(false);
      });
  }, []);

  const article = useMemo(() => parseArticle(markdownContent), [markdownContent]);

  // Research Dropdown Component
  function ResearchDropdown() {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = React.useRef<HTMLDivElement>(null);

    useEffect(() => {
      function handleClickOutside(event: MouseEvent) {
        if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
          setIsOpen(false);
        }
      }
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950"
        >
          <BookOpen className="h-4 w-4" />
          Research
          <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 top-full mt-2 w-72 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg">
            <div className="px-3 py-2">
              <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">Articles</div>
            </div>
            <div className="space-y-1">
              {researchArticles.map((article) => (
                <Link
                  key={article.slug}
                  to={`/research/${article.slug}`}
                  onClick={() => setIsOpen(false)}
                  className="block rounded-xl px-3 py-3 transition-colors hover:bg-zinc-50"
                >
                  <div className="text-sm font-medium text-zinc-900">{article.title}</div>
                  <div className="mt-1 text-xs text-zinc-500 line-clamp-1">{article.subtitle}</div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white text-zinc-950">
      <header className="fixed inset-x-0 top-0 z-40 bg-white/94 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 sm:px-8 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <img src="/brand/worklone-mark-black.png" alt="Worklone" className="h-7 w-auto" />
            <div className="text-lg font-semibold tracking-tight">Worklone</div>
          </Link>

          <div className="flex items-center gap-4">
            <Link to="/" className="hidden text-sm font-medium text-zinc-600 transition-colors hover:text-zinc-950 sm:block">
              Home
            </Link>
            <ResearchDropdown />
            <Link
              to="/waitlist"
              className="inline-flex items-center gap-2 rounded-full bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-800"
            >
              Join Waitlist
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="pt-24">
        <section className="px-6 pb-8 pt-12 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-2xl text-center">
            <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-500">Company Note · April 2026</div>
            <h1 className="mt-4 text-balance text-[34px] font-semibold leading-[1.06] tracking-[-0.04em] text-zinc-950 sm:text-[46px]">
              {article.title}
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-zinc-600 sm:text-[16px] sm:leading-8">
              {article.subtitle}
            </p>
          </div>
        </section>

        <section className="px-6 pb-14 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-5xl">
            <div className="overflow-hidden bg-zinc-200">
              <img
                src="/landinghero.png"
                alt="Worklone editorial visual"
                className="h-[220px] w-full scale-[1.04] object-cover object-center grayscale contrast-125 brightness-90 sm:h-[300px]"
              />
            </div>
          </div>
        </section>

        <section className="px-6 pb-20 sm:px-8 lg:px-10">
          <div className="mx-auto max-w-5xl">
            {loading ? (
              <div className="flex items-center justify-center py-24">
                <div className="text-base text-zinc-500">Loading...</div>
              </div>
            ) : (
              <div className="space-y-16">
                <div className="grid gap-8 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12">
                  <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">
                    Thesis
                  </div>
                  <div>
                    <EditorialMarkdown content={article.intro} compact />
                  </div>
                </div>

                {article.sections.map((section) => (
                  <section
                    key={section.title}
                    className="grid gap-8 border-t border-black/8 pt-12 lg:grid-cols-[160px_minmax(0,680px)] lg:gap-x-12"
                  >
                    <div className="text-[11px] uppercase tracking-[0.22em] text-zinc-400">
                      {section.title}
                    </div>
                    <div>
                      <EditorialMarkdown content={section.body} />
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
