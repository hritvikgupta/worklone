import React, { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FolderOpen, Globe, FileText, Folder, RefreshCw, Share2, Download, Eye, Code2, Copy, Pencil, X, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  getMarkdownContent,
  getMarkdownTree,
  updateMarkdownContent,
  type MarkdownFileContent,
  type MarkdownTreeNode,
} from '@/lib/api';
import { useAuth } from '../../contexts/AuthContext';

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('text-[42px] leading-[1.05] font-semibold tracking-tight text-zinc-950 mb-8', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-10 mb-4 text-[28px] leading-tight font-semibold tracking-tight text-zinc-950', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-8 mb-3 text-[20px] leading-tight font-semibold text-zinc-900', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('mb-5 text-[16px] leading-8 text-zinc-700', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('mb-5 list-disc space-y-2 pl-6 text-[16px] leading-8 text-zinc-700', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('mb-5 list-decimal space-y-2 pl-6 text-[16px] leading-8 text-zinc-700', className)} {...props} />
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
      <table className={cn('w-full border-collapse text-left text-[15px]', className)} {...props} />
    </div>
  ),
  th: ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className={cn('border-b border-zinc-200 px-3 py-2 font-semibold text-zinc-900', className)} {...props} />
  ),
  td: ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className={cn('border-b border-zinc-100 px-3 py-2 text-zinc-700', className)} {...props} />
  ),
};

function flattenFiles(nodes: MarkdownTreeNode[]): MarkdownTreeNode[] {
  return nodes.flatMap((node) => {
    if (node.type === 'file') return [node];
    return node.children ? flattenFiles(node.children) : [];
  });
}

function relativeParts(path: string): string[] {
  return path.split('/').filter(Boolean);
}

function renderTree(
  nodes: MarkdownTreeNode[],
  selectedPath: string,
  onSelect: (node: MarkdownTreeNode) => void
): React.ReactNode {
  return nodes.map((node) => {
    if (node.type === 'folder') {
      return (
        <div key={node.path || node.name} className="space-y-1">
          <div className="flex items-center gap-2 px-3 py-1.5 text-[13px] text-zinc-600">
            <Folder className="w-3.5 h-3.5 text-blue-500" />
            <span className="font-medium">{node.name}</span>
          </div>
          <div className="space-y-1 pl-4">{node.children ? renderTree(node.children, selectedPath, onSelect) : null}</div>
        </div>
      );
    }

    return (
      <button
        key={node.path}
        onClick={() => onSelect(node)}
        className={cn(
          'w-full flex items-center gap-2 rounded-md px-3 py-1.5 text-left text-[13px] transition-colors',
          selectedPath === node.path ? 'bg-zinc-100 text-zinc-900' : 'text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900'
        )}
      >
        <FileText className="w-3.5 h-3.5 text-zinc-400" />
        <span>{node.name}</span>
      </button>
    );
  });
}

export function AgentFilesPage() {
  const { logout } = useAuth();
  const [scope, setScope] = useState<'agent' | 'shared'>('agent');
  const [tree, setTree] = useState<MarkdownTreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState('');
  const [fileContent, setFileContent] = useState<MarkdownFileContent | null>(null);
  const [isCodeView, setIsCodeView] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingTree, setIsLoadingTree] = useState(true);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const files = useMemo(() => flattenFiles(tree), [tree]);

  useEffect(() => {
    let cancelled = false;

    async function loadTree() {
      setIsLoadingTree(true);
      setError(null);
      try {
        const nextTree = await getMarkdownTree(scope);
        if (cancelled) {
          return;
        }
        setTree(nextTree);
        const firstFile = flattenFiles(nextTree)[0];
        setSelectedPath((current) => {
          if (current && flattenFiles(nextTree).some((file) => file.path === current)) {
            return current;
          }
          return firstFile?.path || '';
        });
      } catch (err) {
        if (cancelled) {
          return;
        }
        if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load files');
      } finally {
        if (!cancelled) {
          setIsLoadingTree(false);
        }
      }
    }

    loadTree();
    return () => {
      cancelled = true;
    };
  }, [scope, logout]);

  useEffect(() => {
    if (!selectedPath) {
      setFileContent(null);
      return;
    }

    let cancelled = false;

    async function loadContent() {
      setIsLoadingContent(true);
      setError(null);
      try {
        const content = await getMarkdownContent(scope, selectedPath);
        if (!cancelled) {
          setFileContent(content);
          setDraftContent(content.content);
          setIsEditing(false);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load markdown content');
      } finally {
        if (!cancelled) {
          setIsLoadingContent(false);
        }
      }
    }

    loadContent();
    return () => {
      cancelled = true;
    };
  }, [scope, selectedPath, logout]);

  const selectedFile = files.find((file) => file.path === selectedPath) || files[0] || null;
  const breadcrumb = selectedPath ? relativeParts(selectedPath) : [];

  async function handleRefresh() {
    setIsLoadingTree(true);
    setError(null);
    try {
      const nextTree = await getMarkdownTree(scope);
      setTree(nextTree);
      const nextFiles = flattenFiles(nextTree);
      if (!nextFiles.some((file) => file.path === selectedPath)) {
        setSelectedPath(nextFiles[0]?.path || '');
      }
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to refresh files');
    } finally {
      setIsLoadingTree(false);
    }
  }

  async function handleCopy() {
    if (isEditing) {
      await navigator.clipboard.writeText(draftContent);
      return;
    }
    if (!fileContent?.content) return;
    await navigator.clipboard.writeText(fileContent.content);
  }

  async function handleShare() {
    if (!fileContent?.path) return;
    await navigator.clipboard.writeText(`${scope}:${fileContent.path}`);
  }

  function handleDownload() {
    const contentToDownload = isEditing ? draftContent : fileContent?.content;
    const name = fileContent?.name;
    if (!contentToDownload || !name) return;
    const blob = new Blob([contentToDownload], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    URL.revokeObjectURL(url);
  }

  function handleEditStart() {
    if (!fileContent) return;
    setDraftContent(fileContent.content);
    setIsEditing(true);
  }

  function handleEditCancel() {
    setDraftContent(fileContent?.content || '');
    setIsEditing(false);
  }

  async function handleSave() {
    if (!fileContent) return;
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateMarkdownContent(scope, fileContent.path, draftContent);
      setFileContent(updated);
      setDraftContent(updated.content);
      setIsEditing(false);
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to save markdown content');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="h-full overflow-hidden bg-[#f7f7f5] animate-in slide-in-from-bottom-4 duration-300">
      <div className="h-full flex min-h-0">
        <aside className="w-[300px] shrink-0 border-r border-zinc-200 bg-[#fbfbfa] flex flex-col min-h-0">
          <div className="px-4 pt-4 pb-3 border-b border-zinc-200">
            <div className="grid grid-cols-2 gap-1 rounded-lg bg-zinc-100 p-1">
              <button
                onClick={() => {
                  setScope('agent');
                  setSelectedPath('');
                }}
                className={cn(
                  'flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
                  scope === 'agent' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'
                )}
              >
                <FolderOpen className="w-3.5 h-3.5" />
                Agent
              </button>
              <button
                onClick={() => {
                  setScope('shared');
                  setSelectedPath('');
                }}
                className={cn(
                  'flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
                  scope === 'shared' ? 'bg-white text-zinc-900 shadow-sm' : 'text-zinc-500'
                )}
              >
                <Globe className="w-3.5 h-3.5" />
                Shared
              </button>
            </div>
          </div>

          <div className="px-3 py-3 border-b border-zinc-200 space-y-1">
            {[
              { icon: Eye, label: isCodeView ? 'Preview Mode' : 'Reading Mode' },
              { icon: Code2, label: isCodeView ? 'Source Visible' : 'Source Hidden' },
              { icon: RefreshCw, label: 'Refresh Files', action: handleRefresh },
              { icon: Share2, label: 'Copy File Path', action: handleShare },
            ].map((action) => (
              <button
                key={action.label}
                onClick={action.action}
                className="w-full flex items-center gap-3 rounded-md px-3 py-2 text-[13px] text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors"
              >
                <action.icon className="w-3.5 h-3.5" />
                {action.label}
              </button>
            ))}
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3">
            {isLoadingTree ? (
              <div className="px-3 py-2 text-[13px] text-zinc-500">Loading markdown files...</div>
            ) : error ? (
              <div className="px-3 py-2 text-[13px] text-red-600">{error}</div>
            ) : (
              <div className="space-y-2">{renderTree(tree, selectedFile?.path || '', (node) => setSelectedPath(node.path))}</div>
            )}
          </div>
        </aside>

        <section className="min-w-0 flex-1 bg-white flex flex-col min-h-0">
          <div className="h-14 shrink-0 border-b border-zinc-200 px-6 flex items-center justify-between">
            <div className="text-[13px] text-zinc-500 overflow-hidden text-ellipsis whitespace-nowrap">
              <span className="font-medium text-zinc-700">{scope === 'agent' ? 'Agent Files' : 'Shared Files'}</span>
              {breadcrumb.length > 0 && <span className="mx-2 text-zinc-300">/</span>}
              {breadcrumb.map((part, index) => (
                <span key={`${part}-${index}`}>
                  {index > 0 && <span className="mx-2 text-zinc-300">/</span>}
                  <span className={cn(index === breadcrumb.length - 1 ? 'font-medium text-zinc-900' : '')}>{part}</span>
                </span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                className={cn('h-8 w-8 text-zinc-500 hover:text-zinc-900', !isCodeView && 'bg-zinc-100 text-zinc-900')}
                onClick={() => setIsCodeView(false)}
              >
                <Eye className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn('h-8 w-8 text-zinc-500 hover:text-zinc-900', isCodeView && 'bg-zinc-100 text-zinc-900')}
                onClick={() => setIsCodeView(true)}
              >
                <Code2 className="w-4 h-4" />
              </Button>
              {!isEditing ? (
                <Button variant="ghost" className="h-8 px-3 text-[13px] text-zinc-600 hover:text-zinc-900" onClick={handleEditStart}>
                  <Pencil className="mr-2 h-3.5 w-3.5" />
                  Edit
                </Button>
              ) : (
                <>
                  <Button variant="ghost" className="h-8 px-3 text-[13px] text-zinc-600 hover:text-zinc-900" onClick={handleEditCancel}>
                    <X className="mr-2 h-3.5 w-3.5" />
                    Cancel
                  </Button>
                  <Button className="h-8 px-3 text-[13px] bg-zinc-900 text-white hover:bg-zinc-800" onClick={handleSave} disabled={isSaving}>
                    <Save className="mr-2 h-3.5 w-3.5" />
                    {isSaving ? 'Saving' : 'Save'}
                  </Button>
                </>
              )}
              <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-900" onClick={handleCopy}>
                <Copy className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-900" onClick={handleShare}>
                <Share2 className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-900" onClick={handleDownload}>
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto">
            <div className="w-full px-10 py-8">
              {isLoadingContent ? (
                <div className="text-[14px] text-zinc-500">Loading markdown content...</div>
              ) : error ? (
                <div className="text-[14px] text-red-600">{error}</div>
              ) : !fileContent ? (
                <div className="text-[14px] text-zinc-500">No markdown file selected.</div>
              ) : isEditing ? (
                <textarea
                  value={draftContent}
                  onChange={(event) => setDraftContent(event.target.value)}
                  className={cn(
                    'w-full resize-none rounded-xl border border-zinc-200 bg-white px-5 py-5 outline-none focus:border-zinc-300',
                    isCodeView
                      ? 'min-h-[720px] font-mono text-[13px] leading-6 text-zinc-800'
                      : 'min-h-[720px] text-[15px] leading-8 text-zinc-800'
                  )}
                  spellCheck={false}
                />
              ) : isCodeView ? (
                <pre className="overflow-x-auto text-[13px] leading-6 text-zinc-700 whitespace-pre-wrap break-words font-mono">
                  {fileContent.content}
                </pre>
              ) : (
                <div className="max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {fileContent.content}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
