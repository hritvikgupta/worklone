import React, { useState } from 'react';
import { ChevronRight, ChevronDown, FileText, Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import { FileItem } from '@/src/types';

export function FileTree({
  items,
  selectedFiles,
  onToggle
}: {
  items: FileItem[];
  selectedFiles: string[];
  onToggle: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-1">
      {items.map(item => {
        const isSelected = selectedFiles.includes(item.id);
        const hasChildren = item.children && item.children.length > 0;
        
        return (
          <div key={item.id} className="text-sm">
            <div 
              className={cn(
                "flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors hover:bg-muted/50",
                isSelected && item.type === 'file' ? "bg-primary/10 text-primary hover:bg-primary/20" : "text-foreground"
              )}
              onClick={() => item.type === 'file' ? onToggle(item.id) : toggleExpand(item.id, {} as any)}
            >
              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                {item.type === 'folder' ? (
                  <button onClick={(e) => toggleExpand(item.id, e)} className="hover:bg-muted rounded p-0.5">
                    {expanded[item.id] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                  </button>
                ) : (
                  <div className={cn(
                    "w-3 h-3 rounded-sm border flex items-center justify-center transition-colors",
                    isSelected ? "bg-primary border-primary" : "border-border"
                  )}>
                    {isSelected && <div className="w-1.5 h-1.5 bg-primary-foreground rounded-sm" />}
                  </div>
                )}
              </div>
              {item.type === 'folder' ? (
                <Folder className="w-4 h-4 text-muted-foreground shrink-0" />
              ) : (
                <FileText className={cn("w-4 h-4 shrink-0", isSelected ? "text-primary" : "text-muted-foreground")} />
              )}
              <span className="text-sm truncate">{item.name}</span>
            </div>
            {item.type === 'folder' && expanded[item.id] && item.children && (
              <div className="ml-6 mt-1 border-l border-border/50">
                <FileTree
                  items={item.children}
                  selectedFiles={selectedFiles}
                  onToggle={onToggle}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
