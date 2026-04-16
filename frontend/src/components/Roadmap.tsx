import React, { useMemo, useState } from 'react';
import { Plus, MoreHorizontal, Circle, SlidersHorizontal, LayoutGrid, ExternalLink, X, Clock3, UserCircle2, Bot, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { AnimatePresence, motion } from 'motion/react';

interface RoadmapItem {
  id: string;
  issueKey: string;
  title: string;
  summary: string;
  priority: 'low' | 'medium' | 'high';
  assignee: string;
  agent: string;
  labels: string[];
  description: string;
  process: string;
}

interface Column {
  id: string;
  title: string;
  tone?: 'default' | 'highlight' | 'success';
  items: RoadmapItem[];
}

const initialData: Column[] = [
  {
    id: 'backlog',
    title: 'Backlog',
    items: [
      {
        id: 'item-104',
        issueKey: 'ISSUE-104',
        title: 'Refactor Database Migrations',
        summary: 'Clean up old migration files and optimize the schema.',
        priority: 'medium',
        assignee: 'Hritvik',
        agent: 'Unassigned',
        labels: ['backend', 'migration'],
        description: 'Consolidate old migration files, remove duplicates, and keep schema transitions deterministic.',
        process: 'Audit migration graph, merge redundant scripts, run migrations on clean snapshots, and validate rollback.',
      },
    ],
  },
  {
    id: 'todo',
    title: 'Todo',
    items: [
      {
        id: 'item-103',
        issueKey: 'ISSUE-103',
        title: 'Add Unit Tests for Auth Service',
        summary: 'Increase test coverage for the authentication middleware.',
        priority: 'low',
        assignee: 'Hritvik',
        agent: 'Unassigned',
        labels: ['testing', 'backend'],
        description: 'Expand test coverage for token parsing, token expiry, malformed credentials, and missing auth headers.',
        process: 'Build edge-case tests, verify middleware behavior, and enforce coverage threshold in CI.',
      },
    ],
  },
  {
    id: 'in-progress',
    title: 'In Progress',
    tone: 'highlight',
    items: [
      {
        id: 'item-101',
        issueKey: 'ISSUE-101',
        title: 'Implement Dark Mode Toggle',
        summary: 'Add a theme switcher to the main navigation bar.',
        priority: 'medium',
        assignee: 'Hritvik',
        agent: 'Katy',
        labels: ['frontend', 'theme'],
        description: 'Add persistent dark mode preference and complete theme token coverage across key pages.',
        process: 'Ship nav toggle, persist user preference, then audit all components for theme parity.',
      },
      {
        id: 'item-102',
        issueKey: 'ISSUE-102',
        title: 'Fix Memory Leak in WebAssembly Module',
        summary: 'Investigate and resolve high memory usage in the image worker.',
        priority: 'high',
        assignee: 'Hritvik',
        agent: 'Debug Bot',
        labels: ['performance', 'wasm'],
        description: 'Investigate heap growth in repeated WebAssembly execution and release stale allocations safely.',
        process: 'Profile worker cycles, patch object lifetimes, validate memory stabilization under sustained load.',
      },
    ],
  },
  {
    id: 'in-review',
    title: 'In Review',
    tone: 'success',
    items: [],
  },
];

function priorityClasses(priority: RoadmapItem['priority']): string {
  if (priority === 'high') return 'bg-red-100 text-red-700';
  if (priority === 'medium') return 'bg-amber-100 text-amber-700';
  return 'bg-blue-100 text-blue-700';
}

function headerClasses(tone?: Column['tone']): string {
  if (tone === 'highlight') return 'bg-amber-500 text-white border-amber-500';
  if (tone === 'success') return 'bg-emerald-600 text-white border-emerald-600';
  return 'bg-transparent text-foreground border-transparent';
}

export function Roadmap() {
  const [columns, setColumns] = useState<Column[]>(initialData);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);

  const selectedIssue = useMemo(
    () => columns.flatMap((column) => column.items).find((item) => item.id === selectedIssueId) || null,
    [columns, selectedIssueId]
  );

  const selectedIssueStatus = useMemo(
    () => columns.find((column) => column.items.some((item) => item.id === selectedIssueId))?.title || 'Todo',
    [columns, selectedIssueId]
  );

  const onDragEnd = (result: DropResult) => {
    const { source, destination } = result;
    if (!destination) return;
    if (source.droppableId === destination.droppableId && source.index === destination.index) return;

    const sourceColIndex = columns.findIndex((col) => col.id === source.droppableId);
    const destColIndex = columns.findIndex((col) => col.id === destination.droppableId);
    const sourceCol = columns[sourceColIndex];
    const destCol = columns[destColIndex];
    const sourceItems = [...sourceCol.items];
    const destItems = source.droppableId === destination.droppableId ? sourceItems : [...destCol.items];

    const [removed] = sourceItems.splice(source.index, 1);
    destItems.splice(destination.index, 0, removed);

    const newColumns = [...columns];
    newColumns[sourceColIndex] = { ...sourceCol, items: sourceItems };
    newColumns[destColIndex] = { ...destCol, items: destItems };
    setColumns(newColumns);
  };

  return (
    <div className="relative h-full flex flex-col bg-background overflow-hidden">
      <motion.div
        animate={{
          filter: selectedIssue ? 'blur(2px)' : 'blur(0px)',
          opacity: selectedIssue ? 0.35 : 1,
        }}
        transition={{ duration: 0.2 }}
        className={cn('h-full flex flex-col', selectedIssue && 'pointer-events-none')}
      >
        <div className="px-7 pt-6 pb-4 border-b border-border">
          <h1 className="text-[28px] font-semibold tracking-tight text-foreground">Current Sprint</h1>
          <p className="text-sm text-muted-foreground mt-1">Active tasks and agent assignments for the current cycle.</p>
        </div>

        <div className="px-7 py-3.5 flex items-center gap-2 border-b border-border bg-background">
        <Button className="h-10 px-4 bg-card text-foreground border border-border hover:bg-muted shadow-none">
          <Plus className="w-4 h-4 mr-2" />
          Add Column
        </Button>
        <Button variant="ghost" className="h-10 px-3 text-muted-foreground hover:text-foreground hover:bg-muted">
          <SlidersHorizontal className="w-4 h-4 mr-2" />
          Filter
        </Button>
        <Button variant="ghost" className="h-10 px-3 text-muted-foreground hover:text-foreground hover:bg-muted">
          <LayoutGrid className="w-4 h-4 mr-2" />
          Display
        </Button>
        </div>

        <div className="flex-1 overflow-hidden">
          <DragDropContext onDragEnd={onDragEnd}>
            <div className="flex gap-5 min-w-max h-full overflow-x-auto overflow-y-hidden px-7 py-5">
              {columns.map((column) => (
                <div key={column.id} className="w-[312px] flex-shrink-0 flex flex-col">
                  <div className={cn('rounded-md px-3.5 py-2.5 border flex items-center justify-between', headerClasses(column.tone))}>
                    <div className="flex items-center gap-2.5">
                      <Circle className={cn('w-3.5 h-3.5', column.tone ? 'text-white' : 'text-muted-foreground')} />
                      <span className="text-[15px] font-semibold">{column.title}</span>
                      <span
                        className={cn(
                          'inline-flex items-center justify-center rounded-full min-w-5 h-5 px-1.5 text-[11px] font-semibold',
                          column.tone ? 'bg-card/25 text-white' : 'bg-muted text-foreground'
                        )}
                      >
                        {column.items.length}
                      </span>
                    </div>
                    <div className={cn('flex items-center gap-1', column.tone ? 'text-white/90' : 'text-muted-foreground')}>
                      <Button variant="ghost" size="icon" className={cn('h-6 w-6', column.tone ? 'hover:bg-card/20 hover:text-white' : 'hover:bg-muted hover:text-foreground')}>
                        <MoreHorizontal className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className={cn('h-6 w-6', column.tone ? 'hover:bg-card/20 hover:text-white' : 'hover:bg-muted hover:text-foreground')}>
                        <Plus className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>

                  <Droppable droppableId={column.id}>
                    {(provided, snapshot) => (
                      <div
                        {...provided.droppableProps}
                        ref={provided.innerRef}
                        className={cn(
                          'mt-3 space-y-2.5 rounded-lg flex-1 min-h-[440px] transition-colors',
                          snapshot.isDraggingOver ? 'bg-muted/60 p-2' : ''
                        )}
                      >
                        {column.items.map((item, index) => (
                          /* @ts-expect-error - Draggable key prop is required by React but not in DraggableProps */
                          <Draggable key={item.id} draggableId={item.id} index={index}>
                            {(dragProvided, dragSnapshot) => (
                              <button
                                ref={dragProvided.innerRef}
                                {...dragProvided.draggableProps}
                                {...dragProvided.dragHandleProps}
                                onClick={() => setSelectedIssueId(item.id)}
                                className={cn(
                                  'w-full text-left bg-card border border-border rounded-lg p-4 space-y-2.5 shadow-[0_1px_2px_rgba(0,0,0,0.06)] transition-all hover:shadow-[0_3px_12px_rgba(0,0,0,0.08)]',
                                  dragSnapshot.isDragging && 'border-border shadow-lg rotate-1'
                                )}
                              >
                                <div className="text-muted-foreground text-[11px] font-semibold tracking-wide">{item.issueKey}</div>
                                <h3 className="text-[15px] font-semibold text-foreground leading-snug">{item.title}</h3>
                                <p className="text-[13px] text-muted-foreground leading-6">{item.summary}</p>
                                <div className={cn('inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-bold uppercase tracking-wide w-fit', priorityClasses(item.priority))}>
                                  <Bot className="w-3 h-3" />
                                  {item.priority}
                                </div>
                              </button>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                        <button className="w-full h-10 rounded-md border border-border border-border text-[13px] text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors text-left px-3">
                          <Plus className="w-3.5 h-3.5 inline mr-2" />
                          New
                        </button>
                      </div>
                    )}
                  </Droppable>
                </div>
              ))}
            </div>
          </DragDropContext>
        </div>
      </motion.div>

      <AnimatePresence>
        {selectedIssue && (
          <>
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedIssueId(null)}
              className="absolute inset-0 bg-primary/10 backdrop-blur-[1px] z-30"
              aria-label="Close issue drawer overlay"
            />
            <motion.aside
              initial={{ x: 540 }}
              animate={{ x: 0 }}
              exit={{ x: 540 }}
              transition={{ type: 'spring', damping: 30, stiffness: 260 }}
              className="absolute inset-y-0 right-0 w-[500px] bg-card border-l border-border shadow-[0_10px_40px_rgba(0,0,0,0.08)] flex flex-col z-40"
            >
              <div className="h-14 border-b border-border px-5 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-muted-foreground">{selectedIssue.issueKey.toLowerCase()}</span>
                    <span className="rounded-full border border-border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      {selectedIssueStatus}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                      <ExternalLink className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={() => setSelectedIssueId(null)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
              </div>

              <div className="flex-1 overflow-y-auto px-7 py-6 space-y-6">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-foreground leading-tight">{selectedIssue.title}</h2>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedIssue.labels.map((label) => (
                        <span key={label} className="rounded-md bg-muted px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                          #{label}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="border-t border-border pt-5 grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-[12px] font-bold tracking-wide uppercase text-muted-foreground mb-2">Agent</div>
                      <div className="flex items-center gap-2 text-foreground">
                        <Bot className="w-4 h-4 text-muted-foreground" />
                        <span>{selectedIssue.agent}</span>
                      </div>
                    </div>
                    <div>
                      <div className="text-[12px] font-bold tracking-wide uppercase text-muted-foreground mb-2">Assignee</div>
                      <div className="flex items-center gap-2 text-foreground">
                        <UserCircle2 className="w-4 h-4 text-muted-foreground" />
                        <span>{selectedIssue.assignee}</span>
                      </div>
                    </div>
                  </div>

                  <div className="border-t border-border pt-5">
                    <div className="flex items-center gap-2 text-foreground font-semibold mb-3">
                      <Clock3 className="w-4 h-4 text-muted-foreground" />
                      Task Description
                    </div>
                    <p className="text-muted-foreground leading-relaxed">{selectedIssue.description}</p>
                  </div>

                  <div className="border-t border-border pt-5">
                    <div className="flex items-center gap-2 text-foreground font-semibold mb-3">
                      <RotateCcw className="w-4 h-4 text-muted-foreground" />
                      Agent Process
                    </div>
                    <p className="text-muted-foreground leading-relaxed">{selectedIssue.process}</p>
                  </div>
              </div>

              <div className="border-t border-border p-4">
                <div className="flex items-center gap-2">
                  <input
                    className="flex-1 h-11 rounded-md border border-border px-3 text-sm outline-none focus:border-border"
                    placeholder="Add a comment for the agent..."
                  />
                  <Button className="h-11 px-4 bg-primary text-primary-foreground hover:bg-primary/80">Send</Button>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
