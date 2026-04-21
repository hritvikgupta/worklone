import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  ClipboardCopy,
  Compass,
  FileText,
  Rocket,
  Scale,
  Search,
  Wrench,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarProvider,
} from '@/components/ui/sidebar';

type TocItem = {
  id: string;
  title: string;
  level: 2 | 3;
};

type DocItem = {
  label: string;
  slug: string;
  icon: React.ComponentType<{ className?: string }>;
};

type DocGroup = {
  title: string;
  items: DocItem[];
};

const docGroups: DocGroup[] = [
  {
    title: 'Getting Started',
    items: [
      { label: 'What is Worklone', slug: 'what-is-worklone', icon: CircleHelp },
      { label: 'Quick Start', slug: 'quick-start', icon: Rocket },
      { label: 'Installation', slug: 'installation', icon: Wrench },
    ],
  },
  {
    title: 'Core Concepts',
    items: [
      { label: 'Employee', slug: 'employee', icon: Compass },
      { label: 'Tools', slug: 'tools', icon: Wrench },
      { label: 'Evolution & Memory', slug: 'sdk-evolution', icon: BookOpen },
      { label: 'Human-in-the-Loop', slug: 'human-in-the-loop', icon: Scale },
      { label: 'Sessions & Persistence', slug: 'sessions', icon: FileText },
    ],
  },
  {
    title: 'Integrations',
    items: [
      { label: 'Overview', slug: 'integrations', icon: Compass },
      { label: 'Gmail', slug: 'integration-gmail', icon: FileText },
      { label: 'Slack', slug: 'integration-slack', icon: FileText },
      { label: 'GitHub', slug: 'integration-github', icon: FileText },
      { label: 'Linear', slug: 'integration-linear', icon: FileText },
      { label: 'Stripe', slug: 'integration-stripe', icon: FileText },
      { label: 'HubSpot', slug: 'integration-hubspot', icon: FileText },
    ],
  },
  {
    title: 'API Reference',
    items: [
      { label: 'Employee Class', slug: 'api-employee', icon: FileText },
      { label: 'BaseTool', slug: 'api-basetool', icon: FileText },
      { label: 'TokenStore', slug: 'api-tokenstore', icon: FileText },
    ],
  },
  {
    title: 'Examples',
    items: [
      { label: 'Personal Assistant', slug: 'example-personal-assistant', icon: Rocket },
      { label: 'Sales Rep', slug: 'example-sales-rep', icon: Rocket },
      { label: 'Engineering Lead', slug: 'example-engineering-lead', icon: Rocket },
      { label: 'Research Analyst', slug: 'example-research-analyst', icon: Rocket },
      { label: 'HR Recruiter', slug: 'example-hr-recruiter', icon: Rocket },
      { label: 'Finance Controller', slug: 'example-finance-controller', icon: Rocket },
    ],
  },
];

const allDocs = docGroups.flatMap((group) => group.items);


function slugify(value: string) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-');
}

function extractToc(markdown: string): TocItem[] {
  return markdown
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('## ') || line.startsWith('### '))
    .map((line) => {
      if (line.startsWith('### ')) {
        const title = line.replace(/^###\s+/, '').trim();
        return { title, id: slugify(title), level: 3 as const };
      }
      const title = line.replace(/^##\s+/, '').trim();
      return { title, id: slugify(title), level: 2 as const };
    });
}

function CodeBlock({ lang, children }: { lang: string; children: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="group relative mt-5 mb-1 rounded-xl border border-zinc-200 bg-[#f8f9fa] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-200 bg-zinc-50">
        <span className="text-[11px] font-medium text-zinc-400 uppercase tracking-widest">
          {lang || 'code'}
        </span>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-green-500" />
              <span className="text-green-600">Copied</span>
            </>
          ) : (
            <>
              <ClipboardCopy className="h-3.5 w-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <SyntaxHighlighter
        language={lang || 'text'}
        style={oneLight}
        customStyle={{
          margin: 0,
          padding: '1rem 1.25rem',
          borderRadius: 0,
          fontSize: '13.5px',
          lineHeight: '1.7',
          background: '#f8f9fa',
          border: 'none',
        }}
        codeTagProps={{ style: { fontFamily: 'ui-monospace, "Fira Code", "Cascadia Code", monospace' } }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

export function DocumentationPage() {
  const { docSlug } = useParams<{ docSlug?: string }>();
  const navigate = useNavigate();
  const slug = docSlug || 'quick-start';

  const activeDoc = useMemo(
    () => allDocs.find((item) => item.slug === slug),
    [slug]
  );

  const [markdownContent, setMarkdownContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('');
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeDoc) return;
    setLoading(true);
    fetch(`/docs/${activeDoc.slug}.md`)
      .then((res) => {
        if (!res.ok) throw new Error('missing');
        return res.text();
      })
      .then((text) => setMarkdownContent(text))
      .catch(() => setMarkdownContent('# Missing Page\n\n## Not Found\n\nThis markdown file is not available yet.'))
      .finally(() => setLoading(false));
  }, [activeDoc]);

  const toc = useMemo(() => extractToc(markdownContent), [markdownContent]);

  useEffect(() => {
    if (!toc.length || !contentRef.current) return;
    setActiveSection(toc[0].id);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.find((entry) => entry.isIntersecting);
        if (visible?.target.id) setActiveSection(visible.target.id);
      },
      { root: contentRef.current, rootMargin: '-10% 0px -75% 0px', threshold: 0.01 }
    );

    toc.forEach((section) => {
      const node = document.getElementById(section.id);
      if (node) observer.observe(node);
    });

    return () => observer.disconnect();
  }, [toc, activeDoc?.slug]);

  const commandResults = useMemo(() => {
    const value = commandQuery.trim().toLowerCase();
    const docs = allDocs
      .filter((item) => !value || item.label.toLowerCase().includes(value))
      .map((item) => ({
        id: `doc:${item.slug}`,
        label: item.label,
        type: 'doc' as const,
        meta: 'Page',
        slug: item.slug,
      }));

    const sections = toc
      .filter((item) => !value || item.title.toLowerCase().includes(value))
      .map((item) => ({
        id: `section:${item.id}`,
        label: item.title,
        type: 'section' as const,
        meta: 'Section',
        sectionId: item.id,
      }));

    return [...docs, ...sections];
  }, [commandQuery, toc]);

  useEffect(() => {
    const handleShortcut = (event: KeyboardEvent) => {
      const isCmdK = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k';
      if (!isCmdK) return;
      event.preventDefault();
      setIsCommandOpen(true);
    };
    window.addEventListener('keydown', handleShortcut);
    return () => window.removeEventListener('keydown', handleShortcut);
  }, []);

  const markdownComponents: Record<string, React.ComponentType<any>> = {
    h1: ({ children }: any) => (
      <h1 className="mt-2 mb-4 text-[32px] font-bold tracking-tight text-zinc-950 leading-tight">
        {children}
      </h1>
    ),
    h2: ({ children }: any) => {
      const title = String(children ?? '');
      return (
        <h2
          id={slugify(title)}
          className="mt-10 mb-3 scroll-mt-20 border-t border-zinc-200 pt-8 text-[22px] font-semibold tracking-tight text-zinc-900"
        >
          {children}
        </h2>
      );
    },
    h3: ({ children }: any) => {
      const title = String(children ?? '');
      return (
        <h3
          id={slugify(title)}
          className="mt-7 mb-2 scroll-mt-20 text-[17px] font-semibold text-zinc-900"
        >
          {children}
        </h3>
      );
    },
    h4: ({ children }: any) => (
      <h4 className="mt-5 mb-1 text-[15px] font-semibold text-zinc-800">{children}</h4>
    ),
    p: ({ children }: any) => (
      <p className="mt-4 text-[15px] leading-7 text-zinc-600">{children}</p>
    ),
    ul: ({ children }: any) => (
      <ul className="mt-4 space-y-1.5 pl-5 text-[15px] leading-7 text-zinc-600 list-disc marker:text-zinc-400">
        {children}
      </ul>
    ),
    ol: ({ children }: any) => (
      <ol className="mt-4 space-y-1.5 pl-5 text-[15px] leading-7 text-zinc-600 list-decimal marker:text-zinc-400">
        {children}
      </ol>
    ),
    li: ({ children }: any) => (
      <li className="pl-1">{children}</li>
    ),
    strong: ({ children }: any) => (
      <strong className="font-semibold text-zinc-900">{children}</strong>
    ),
    em: ({ children }: any) => (
      <em className="italic text-zinc-700">{children}</em>
    ),
    a: ({ href, children }: any) => {
      const isInternal = href?.startsWith('/docs/');
      if (isInternal) {
        const slug = href.replace('/docs/', '');
        return (
          <Link
            to={`/documentation/${slug}`}
            className="font-medium text-blue-600 underline underline-offset-2 decoration-blue-300 hover:text-blue-800 hover:decoration-blue-500 transition-colors"
          >
            {children}
          </Link>
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-blue-600 underline underline-offset-2 decoration-blue-300 hover:text-blue-800 hover:decoration-blue-500 transition-colors"
        >
          {children}
        </a>
      );
    },
    blockquote: ({ children }: any) => (
      <blockquote className="mt-4 border-l-4 border-zinc-300 pl-4 text-[15px] italic text-zinc-500">
        {children}
      </blockquote>
    ),
    hr: () => <hr className="my-8 border-zinc-200" />,
    table: ({ children }: any) => (
      <div className="mt-6 overflow-x-auto rounded-xl border border-zinc-200">
        <table className="w-full text-[14px] text-left">{children}</table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead className="bg-zinc-50 border-b border-zinc-200">{children}</thead>
    ),
    tbody: ({ children }: any) => (
      <tbody className="divide-y divide-zinc-100">{children}</tbody>
    ),
    tr: ({ children }: any) => <tr>{children}</tr>,
    th: ({ children }: any) => (
      <th className="px-4 py-3 font-semibold text-zinc-700 text-[13px] uppercase tracking-wide">
        {children}
      </th>
    ),
    td: ({ children }: any) => (
      <td className="px-4 py-3 text-zinc-600 align-top">{children}</td>
    ),
    code: ({ className, children, inline }: any) => {
      const lang = (className || '').replace('language-', '');
      if (inline || !lang) {
        return (
          <code className="rounded-md bg-zinc-100 px-1.5 py-0.5 font-mono text-[13px] text-zinc-800 border border-zinc-200">
            {children}
          </code>
        );
      }
      return (
        <CodeBlock lang={lang}>
          {String(children).replace(/\n$/, '')}
        </CodeBlock>
      );
    },
    pre: ({ children }: any) => (
      <div className="mt-5 mb-1">{children}</div>
    ),
  };

  const scrollToSection = (id: string) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setActiveSection(id);
  };

  const handleCommandSelect = (item: (typeof commandResults)[number]) => {
    if (item.type === 'doc') {
      navigate(`/documentation/${item.slug}`);
    } else {
      scrollToSection(item.sectionId);
    }
    setIsCommandOpen(false);
    setCommandQuery('');
  };

  if (!activeDoc) {
    return <Navigate to="/documentation/quick-start" replace />;
  }

  return (
    <div className="h-screen overflow-hidden bg-[#f3f5f9] text-zinc-950">
      <header className="fixed inset-x-0 top-0 z-40 bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1480px] items-center gap-4 px-4 sm:px-6">
          <Link to="/" className="flex shrink-0 items-center gap-3">
            <img src="/brand/worklone-mark-black.png" alt="Worklone" className="h-7 w-auto" />
            <span className="text-[21px] font-semibold tracking-tight">Worklone</span>
          </Link>

          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={() => setIsCommandOpen(true)}
              className="relative flex w-full min-w-[220px] max-w-[280px] items-center gap-3 rounded-2xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-left text-zinc-500 transition-colors hover:bg-zinc-100"
            >
              <Search className="h-4 w-4 text-zinc-400" />
              <span className="text-[16px]">Search...</span>
              <span className="ml-auto flex items-center gap-1">
                <span className="rounded-md border border-zinc-300 bg-white px-1.5 py-0.5 text-[12px] text-zinc-500">⌘</span>
                <span className="rounded-md border border-zinc-300 bg-white px-1.5 py-0.5 text-[12px] text-zinc-500">K</span>
              </span>
            </button>

            <Link
              to="/waitlist"
              className="inline-flex items-center gap-1.5 rounded-full bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-zinc-800"
            >
              Join Waitlist
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <SidebarProvider
        className="pt-16"
        style={{ "--sidebar-width": "18.5rem" } as React.CSSProperties}
      >
        <div className="h-[calc(100vh-64px)] w-full">
          <Sidebar
            collapsible="none"
            className="fixed top-16 left-0 z-20 hidden h-[calc(100vh-64px)] w-[300px] border-r border-sidebar-border/70 bg-sidebar lg:flex"
          >
            <SidebarContent className="py-3">
              <ScrollArea className="h-full px-2">
                {docGroups.map((group) => (
                  <SidebarGroup key={group.title} className="gap-1 px-1 py-1.5">
                    <SidebarGroupLabel className="h-6 px-2 text-[13px] font-semibold text-zinc-800/90">
                      {group.title}
                    </SidebarGroupLabel>
                    <div className="space-y-1">
                      {group.items.map((item) => {
                        const Icon = item.icon;
                        const isActive = item.slug === activeDoc.slug;
                        return (
                          <Link
                            key={item.slug}
                            to={`/documentation/${item.slug}`}
                            className={cn(
                              'flex h-8 items-center gap-2 rounded-lg px-2 text-[13px] transition-colors',
                              isActive
                                ? 'bg-zinc-900 text-white'
                                : 'bg-transparent text-zinc-800 hover:bg-zinc-100'
                            )}
                          >
                            <Icon className="h-3.5 w-3.5" />
                            <span>{item.label}</span>
                          </Link>
                        );
                      })}
                    </div>
                  </SidebarGroup>
                ))}
              </ScrollArea>
            </SidebarContent>
          </Sidebar>

          <main
            ref={contentRef}
            className="h-[calc(100vh-64px)] overflow-y-auto bg-white px-10 pb-20 pt-10 lg:ml-[300px] xl:mr-[280px]"
          >
            <article className="w-full max-w-[760px]">
              {loading ? (
                <div className="py-16 text-zinc-500">Loading documentation...</div>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {markdownContent}
                </ReactMarkdown>
              )}
            </article>
          </main>

          <aside className="fixed top-16 right-0 hidden h-[calc(100vh-64px)] w-[280px] border-l border-zinc-200 bg-white xl:block">
            <ScrollArea className="h-full px-5 py-8">
              <div className="text-sm font-medium text-zinc-500">On this page</div>
              <nav className="mt-4 space-y-1 border-l border-zinc-200 pl-3">
                {toc.map((section) => (
                  <a
                    key={`${section.level}-${section.id}`}
                    href={`#${section.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      scrollToSection(section.id);
                    }}
                    className={cn(
                      'block py-1 text-[14px] transition-colors',
                      section.level === 3 && 'pl-3 text-[13px]',
                      activeSection === section.id ? 'text-sky-700' : 'text-zinc-500 hover:text-zinc-900'
                    )}
                  >
                    {section.title}
                  </a>
                ))}
              </nav>
            </ScrollArea>
          </aside>
        </div>
      </SidebarProvider>

      <Dialog open={isCommandOpen} onOpenChange={setIsCommandOpen}>
        <DialogContent
          showCloseButton={false}
          className="max-w-[680px] gap-0 overflow-hidden rounded-2xl border border-zinc-300 bg-white p-0"
        >
          <div className="border-b border-zinc-200 p-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
              <Input
                autoFocus
                value={commandQuery}
                onChange={(e) => setCommandQuery(e.target.value)}
                placeholder="Search documentation..."
                className="h-11 rounded-xl border-zinc-300 bg-white pl-9 text-[16px]"
              />
            </div>
          </div>

          <div className="px-4 pt-3 text-xs font-semibold uppercase tracking-[0.08em] text-zinc-500">Sections</div>
          <ScrollArea className="h-[340px] px-2 py-2">
            <div className="space-y-1">
              {commandResults.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleCommandSelect(item)}
                  className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left hover:bg-zinc-100"
                >
                  <span className="flex items-center gap-2 text-zinc-700">
                    <ChevronRight className="h-4 w-4" />
                    <span className="text-base">{item.label}</span>
                  </span>
                  <span className="text-xs text-zinc-500">{item.meta}</span>
                </button>
              ))}
              {!commandResults.length ? (
                <div className="px-3 py-6 text-sm text-zinc-500">No results found.</div>
              ) : null}
            </div>
          </ScrollArea>

          <div className="border-t border-zinc-200 px-4 py-3 text-sm text-zinc-500">↵ Go to Page</div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
