import React, { useEffect, useMemo, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, FileImage, File, Upload, RefreshCw, Share2, Download, Eye, Code2, Copy, Pencil, X, Save, FileType2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  CHAT_AUTH_EXPIRED_ERROR,
  getMarkdownContent,
  getMarkdownTree,
  updateMarkdownContent,
  uploadFile,
  fetchRawFileBlob,
  type MarkdownFileContent,
  type MarkdownTreeNode,
} from '@/lib/api';
import { useAuth } from '../../contexts/AuthContext';

const markdownComponents = {
  h1: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className={cn('text-[42px] leading-[1.05] font-semibold tracking-tight text-foreground mb-8', className)} {...props} />
  ),
  h2: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className={cn('mt-10 mb-4 text-[28px] leading-tight font-semibold tracking-tight text-foreground', className)} {...props} />
  ),
  h3: ({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className={cn('mt-8 mb-3 text-[20px] leading-tight font-semibold text-foreground', className)} {...props} />
  ),
  p: ({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className={cn('mb-5 text-[16px] leading-8 text-foreground', className)} {...props} />
  ),
  ul: ({ className, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className={cn('mb-5 list-disc space-y-2 pl-6 text-[16px] leading-8 text-foreground', className)} {...props} />
  ),
  ol: ({ className, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className={cn('mb-5 list-decimal space-y-2 pl-6 text-[16px] leading-8 text-foreground', className)} {...props} />
  ),
  li: ({ className, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className={cn('pl-1', className)} {...props} />
  ),
  hr: (props: React.HTMLAttributes<HTMLHRElement>) => <hr className="my-8 border-border" {...props} />,
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
      <table className={cn('w-full border-collapse text-left text-[15px]', className)} {...props} />
    </div>
  ),
  th: ({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className={cn('border-b border-border px-3 py-2 font-semibold text-foreground', className)} {...props} />
  ),
  td: ({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className={cn('border-b border-border px-3 py-2 text-foreground', className)} {...props} />
  ),
};

function flattenFiles(nodes: MarkdownTreeNode[]): MarkdownTreeNode[] {
  return nodes.flatMap((node) => {
    if (node.type === 'file') return [node];
    return node.children ? flattenFiles(node.children) : [];
  });
}

function getFileIcon(name: string) {
  const lower = name.toLowerCase();
  if (lower.endsWith('.pdf')) return <FileType2 className="w-4 h-4 text-rose-500" />;
  if (lower.endsWith('.md')) return <FileText className="w-4 h-4 text-blue-500" />;
  if (lower.endsWith('.txt')) return <File className="w-4 h-4 text-zinc-500" />;
  return <File className="w-4 h-4 text-muted-foreground" />;
}

export function AgentFilesPage() {
  const { logout } = useAuth();
  const [files, setFiles] = useState<MarkdownTreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState('');
  const [fileContent, setFileContent] = useState<MarkdownFileContent | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isCodeView, setIsCodeView] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(true);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadFiles = async () => {
    setIsLoadingFiles(true);
    setError(null);
    try {
      const nextTree = await getMarkdownTree('agent');
      const flatFiles = flattenFiles(nextTree);
      setFiles(flatFiles);
      
      setSelectedPath((current) => {
        if (current && flatFiles.some((file) => file.path === current)) {
          return current;
        }
        return flatFiles[0]?.path || '';
      });
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load files');
    } finally {
      setIsLoadingFiles(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, [logout]);

  useEffect(() => {
    if (!selectedPath) {
      setFileContent(null);
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
      return;
    }

    let cancelled = false;

    async function loadContent() {
      setIsLoadingContent(true);
      setError(null);
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
        setBlobUrl(null);
      }
      
      try {
        if (selectedPath.toLowerCase().endsWith('.pdf')) {
          const blob = await fetchRawFileBlob('agent', selectedPath);
          if (!cancelled) {
            const url = URL.createObjectURL(blob);
            setBlobUrl(url);
            setFileContent({ scope: 'agent', root_name: 'Root', path: selectedPath, name: selectedPath.split('/').pop() || '', content: '' });
          }
        } else {
          const content = await getMarkdownContent('agent', selectedPath);
          if (!cancelled) {
            setFileContent(content);
            setDraftContent(content.content);
            setIsEditing(false);
          }
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
          logout();
          return;
        }
        setError(err instanceof Error ? err.message : 'Failed to load file content');
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
  }, [selectedPath, logout]);

  // Clean up object URLs on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  const selectedFile = files.find((file) => file.path === selectedPath) || files[0] || null;
  const isEditable = selectedFile?.name.toLowerCase().endsWith('.md') || selectedFile?.name.toLowerCase().endsWith('.txt');

  async function handleRefresh() {
    await loadFiles();
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
    if (!selectedFile?.path) return;
    await navigator.clipboard.writeText(selectedFile.path);
  }

  function handleDownload() {
    if (blobUrl && selectedFile?.name.toLowerCase().endsWith('.pdf')) {
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = selectedFile.name;
      link.click();
      return;
    }
    
    const contentToDownload = isEditing ? draftContent : fileContent?.content;
    const name = selectedFile?.name;
    if (!contentToDownload || !name) return;
    const blob = new Blob([contentToDownload], { type: 'text/plain;charset=utf-8' });
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
      const updated = await updateMarkdownContent('agent', fileContent.path, draftContent);
      setFileContent(updated);
      setDraftContent(updated.content);
      setIsEditing(false);
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to save file content');
    } finally {
      setIsSaving(false);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    try {
      await uploadFile('agent', file);
      await loadFiles();
      // Select the newly uploaded file
      setSelectedPath(file.name);
    } catch (err) {
      if (err instanceof Error && err.message === CHAT_AUTH_EXPIRED_ERROR) {
        logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  return (
    <div className="h-full overflow-hidden bg-background animate-in slide-in-from-bottom-4 duration-300">
      <div className="h-full flex min-h-0">
        <aside className="w-[300px] shrink-0 border-r border-border bg-sidebar flex flex-col min-h-0">
          <div className="px-4 py-4 border-b border-border flex flex-col gap-3">
            <h3 className="font-semibold text-foreground text-sm">Your Files</h3>
            <Button 
              onClick={() => fileInputRef.current?.click()} 
              disabled={isUploading}
              className="w-full gap-2"
            >
              <Upload className="w-4 h-4" />
              {isUploading ? 'Uploading...' : 'Upload File'}
            </Button>
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept=".pdf,.md,.txt" 
              onChange={handleFileUpload} 
            />
            <p className="text-[10px] text-muted-foreground text-center">Supported: PDF, TXT, MD</p>
          </div>

          <div className="px-3 py-2 border-b border-border">
            <button
              onClick={handleRefresh}
              className="w-full flex items-center gap-3 rounded-md px-3 py-2 text-[13px] text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh List
            </button>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3">
            {isLoadingFiles ? (
              <div className="px-3 py-2 text-[13px] text-muted-foreground">Loading files...</div>
            ) : error ? (
              <div className="px-3 py-2 text-[13px] text-red-600">{error}</div>
            ) : files.length === 0 ? (
              <div className="px-3 py-4 text-[13px] text-muted-foreground text-center italic">No files uploaded yet.</div>
            ) : (
              <div className="space-y-1">
                {files.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => setSelectedPath(file.path)}
                    className={cn(
                      'w-full flex items-center gap-2.5 rounded-md px-3 py-2 text-left text-[13px] transition-colors',
                      selectedPath === file.path ? 'bg-primary/10 text-primary font-medium' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    {getFileIcon(file.name)}
                    <span className="truncate flex-1">{file.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </aside>

        <section className="min-w-0 flex-1 bg-card flex flex-col min-h-0">
          <div className="h-14 shrink-0 border-b border-border px-6 flex items-center justify-between">
            <div className="text-[14px] font-medium text-foreground truncate max-w-[50%]">
              {selectedFile?.name || 'Select a file'}
            </div>
            <div className="flex items-center gap-2">
              {isEditable && (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn('h-8 w-8 text-muted-foreground hover:text-foreground', !isCodeView && 'bg-muted text-foreground')}
                    onClick={() => setIsCodeView(false)}
                  >
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={cn('h-8 w-8 text-muted-foreground hover:text-foreground', isCodeView && 'bg-muted text-foreground')}
                    onClick={() => setIsCodeView(true)}
                  >
                    <Code2 className="w-4 h-4" />
                  </Button>
                  {!isEditing ? (
                    <Button variant="ghost" className="h-8 px-3 text-[13px] text-muted-foreground hover:text-foreground" onClick={handleEditStart}>
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      Edit
                    </Button>
                  ) : (
                    <>
                      <Button variant="ghost" className="h-8 px-3 text-[13px] text-muted-foreground hover:text-foreground" onClick={handleEditCancel}>
                        <X className="mr-2 h-3.5 w-3.5" />
                        Cancel
                      </Button>
                      <Button className="h-8 text-[13px]" onClick={handleSave} disabled={isSaving}>
                        <Save className="mr-2 h-3.5 w-3.5" />
                        {isSaving ? 'Saving' : 'Save'}
                      </Button>
                    </>
                  )}
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={handleCopy}>
                    <Copy className="w-4 h-4" />
                  </Button>
                </>
              )}
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={handleShare} disabled={!selectedFile}>
                <Share2 className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={handleDownload} disabled={!selectedFile}>
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto">
            {isLoadingContent ? (
               <div className="w-full px-10 py-8 text-[14px] text-muted-foreground flex items-center justify-center h-full">Loading file content...</div>
            ) : error ? (
               <div className="w-full px-10 py-8 text-[14px] text-red-600 flex items-center justify-center h-full">{error}</div>
            ) : !selectedFile ? (
               <div className="w-full px-10 py-8 text-[14px] text-muted-foreground flex items-center justify-center h-full">No file selected.</div>
            ) : blobUrl && selectedFile.name.toLowerCase().endsWith('.pdf') ? (
              <iframe 
                src={blobUrl} 
                className="w-full h-full border-none"
                title={selectedFile.name}
              />
            ) : isEditing ? (
              <div className="w-full px-10 py-8 h-full">
                <textarea
                  value={draftContent}
                  onChange={(event) => setDraftContent(event.target.value)}
                  className={cn(
                    'w-full h-full resize-none rounded-xl border border-input bg-background px-5 py-5 outline-none focus:border-ring',
                    isCodeView
                      ? 'font-mono text-[13px] leading-6 text-foreground'
                      : 'text-[15px] leading-8 text-foreground'
                  )}
                  spellCheck={false}
                />
              </div>
            ) : (
              <div className="w-full px-10 py-8">
                {isCodeView || selectedFile.name.toLowerCase().endsWith('.txt') ? (
                  <pre className="overflow-x-auto text-[13px] leading-6 text-muted-foreground whitespace-pre-wrap break-words font-mono">
                    {fileContent?.content}
                  </pre>
                ) : (
                  <div className="max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {fileContent?.content || ''}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
