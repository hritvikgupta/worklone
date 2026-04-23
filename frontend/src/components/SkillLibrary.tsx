import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, Loader2, Plus, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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

function stripFrontmatter(markdown: string): string {
  if (!markdown.startsWith('---')) return markdown.trim();
  return markdown.replace(/^---\n[\s\S]*?\n---\n?/m, '').trim();
}

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('text-2xl font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-8 text-xl font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-6 text-lg font-semibold text-foreground', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('my-4 text-sm leading-7 text-foreground', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('my-4 list-disc space-y-1 pl-6 text-sm text-foreground', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('my-4 list-decimal space-y-1 pl-6 text-sm text-foreground', className)} {...props} />
  ),
  pre: ({ className, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className={cn('my-4 overflow-x-auto rounded-lg border border-border bg-muted p-3 text-xs', className)} {...props} />
  ),
  code: ({ className, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <code className={cn('rounded bg-muted px-1 py-0.5 text-xs', className)} {...props} />
  ),
};

function getSkillSourceBadge(skill: PublicSkillListItem): string {
  const source = (skill.source_model || '').toLowerCase();
  const notes = ((skill as PublicSkillDetail).notes || '').toLowerCase();
  const role = (skill.employee_role || '').toLowerCase();

  if (source === 'agency-skills-import' || notes.includes('imported from')) return 'Library';
  if (source.startsWith('provision:')) return 'AI Provisioning';
  if (source.startsWith('user:')) return 'Users';
  if (source && role !== 'general workplace') return 'AI Provisioning';
  if (source) return 'Users';
  if (role !== 'general workplace') return 'AI Provisioning';
  return 'Users';
}

export function SkillLibrary() {
  const { logout } = useAuth();
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedSource, setSelectedSource] = useState('All');
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

    void loadSkills();
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

    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedSkill, logout]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const skill of skills) {
      const cat = skill.category || 'general';
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [skills]);

  const categories = useMemo(() => {
    const unique = Array.from(new Set(skills.map((s) => s.category || 'general'))).sort();
    return ['All', ...unique];
  }, [skills]);

  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = { Users: 0, 'AI Provisioning': 0, Library: 0 };
    for (const skill of skills) {
      const source = getSkillSourceBadge(skill);
      counts[source] = (counts[source] || 0) + 1;
    }
    return counts;
  }, [skills]);

  const sourceOptions = useMemo(() => ['All', 'Users', 'AI Provisioning', 'Library'], []);

  const filteredSkills = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return skills.filter((skill) => {
      const matchesCategory = selectedCategory === 'All' || skill.category === selectedCategory;
      if (!matchesCategory) return false;
      const sourceLabel = getSkillSourceBadge(skill);
      const matchesSource = selectedSource === 'All' || sourceLabel === selectedSource;
      if (!matchesSource) return false;
      if (!normalized) return true;
      const sourceLabelLower = sourceLabel.toLowerCase();
      const sourceModel = (skill.source_model || '').toLowerCase();
      return (
        skill.title.toLowerCase().includes(normalized) ||
        skill.category.toLowerCase().includes(normalized) ||
        skill.employee_role.toLowerCase().includes(normalized) ||
        skill.description.toLowerCase().includes(normalized) ||
        sourceLabelLower.includes(normalized) ||
        sourceModel.includes(normalized)
      );
    });
  }, [query, selectedCategory, selectedSource, skills]);

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

  return (
    <div className="w-full p-0">
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">Find Skills</h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Browse categories and search across your local skills library.
            </p>
          </div>
          <Button onClick={() => setCreationModalOpen(true)} className="h-9 gap-2 px-3 text-sm">
            <Plus className="h-4 w-4" />
            Create Skill
          </Button>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search all skills"
            className="h-10 rounded-lg pl-9 text-sm"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button type="button" variant="outline" className="h-9 gap-2 rounded-full px-4 text-sm">
                Filters
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-72">
              <DropdownMenuLabel>Source</DropdownMenuLabel>
              <DropdownMenuRadioGroup value={selectedSource} onValueChange={setSelectedSource}>
                {sourceOptions.map((source) => {
                  const count = source === 'All' ? skills.length : sourceCounts[source] || 0;
                  return (
                    <DropdownMenuRadioItem key={source} value={source}>
                      {source} {count}
                    </DropdownMenuRadioItem>
                  );
                })}
              </DropdownMenuRadioGroup>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Category</DropdownMenuLabel>
              <DropdownMenuRadioGroup value={selectedCategory} onValueChange={setSelectedCategory}>
                {categories.map((category) => {
                  const count = category === 'All' ? skills.length : categoryCounts[category] || 0;
                  return (
                    <DropdownMenuRadioItem key={category} value={category}>
                      {category} {count}
                    </DropdownMenuRadioItem>
                  );
                })}
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <Badge variant="outline" className="h-8 rounded-full px-3 text-xs">
            {selectedSource === 'All' ? 'All Sources' : selectedSource}
          </Badge>
          <Badge variant="outline" className="h-8 rounded-full px-3 text-xs">
            {selectedCategory === 'All' ? 'All Categories' : selectedCategory}
          </Badge>
          <Badge variant="secondary" className="h-8 rounded-full px-3 text-xs">
            {filteredSkills.length} shown
          </Badge>
        </div>

        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {isLoadingList ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading public skills...
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {filteredSkills.map((skill) => (
              <Card
                key={skill.id}
                className="cursor-pointer rounded-xl border-border/80 bg-background py-0 transition-colors hover:bg-muted/30"
                onClick={() => setSelectedSkill(skill)}
              >
                <CardContent className="space-y-2 px-4 py-4 text-left">
                  <div className="flex justify-end gap-1">
                    <Badge variant="outline" className="rounded-full px-2 py-0.5 text-[9px] uppercase tracking-wide text-muted-foreground">
                      {skill.category}
                    </Badge>
                    <Badge variant="secondary" className="rounded-full px-2 py-0.5 text-[9px] uppercase tracking-wide">
                      {getSkillSourceBadge(skill)}
                    </Badge>
                  </div>
                  <h3 className="text-xl font-semibold tracking-tight text-foreground">{skill.title}</h3>
                  <p className="max-w-[52ch] text-xs leading-5 text-muted-foreground">
                    {skill.description || skill.employee_role || 'Reusable workplace capability module.'}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={Boolean(selectedSkill)} onOpenChange={(open) => { if (!open) setSelectedSkill(null); }}>
        <DialogContent className="!w-[98vw] !max-w-[98vw] sm:!max-w-[1400px] overflow-hidden p-0">
          <div className="flex h-[85vh] min-h-0 flex-col">
            <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
              <DialogTitle>{selectedSkill?.title || 'Skill Detail'}</DialogTitle>
              <DialogDescription>
                {selectedSkill?.employee_role || selectedSkill?.category || ''}
              </DialogDescription>
            </DialogHeader>

            <div className="min-h-0 flex-1 overflow-y-auto overflow-x-auto px-6 py-5">
              {isLoadingDetail || !skillDetail ? (
                <div className="text-sm text-muted-foreground">Loading skill details...</div>
              ) : (
                <div className="space-y-6">
                  <Card className="py-0">
                    <CardContent className="px-5 py-4 text-sm leading-7 text-foreground">
                      {skillDetail.description}
                    </CardContent>
                  </Card>

                  {skillDetail.skill_markdown ? (
                    <article className="prose prose-zinc max-w-none break-words [&_h1]:break-words [&_h2]:break-words [&_h3]:break-words [&_p]:break-words [&_p]:whitespace-normal [&_li]:break-words [&_li]:whitespace-normal [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_code]:break-all">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {stripFrontmatter(skillDetail.skill_markdown)}
                      </ReactMarkdown>
                    </article>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={creationModalOpen} onOpenChange={(open) => { if (!isCreating) setCreationModalOpen(open); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Public Skill</DialogTitle>
            <DialogDescription>Generate and add a new skill into the shared public skill library.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Skill Name</label>
              <Input
                value={createTitle}
                onChange={(e) => setCreateTitle(e.target.value)}
                placeholder="e.g. Inbox Triage and Action Routing"
                disabled={isCreating}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                placeholder="What should this skill do and when to use it..."
                rows={4}
                disabled={isCreating}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setCreationModalOpen(false)} disabled={isCreating}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateSkill}
              disabled={isCreating || !createTitle.trim() || !createDescription.trim()}
            >
              {isCreating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                'Create Skill'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
