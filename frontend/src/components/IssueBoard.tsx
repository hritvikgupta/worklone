import React, { useRef, useState } from 'react';
import { Issue, IssueStatus } from '@/src/types';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { listEmployees, EmployeeDetail } from '@/src/api/employees';
import { motion, AnimatePresence } from 'motion/react';
import { 
  MoreHorizontal, 
  Plus, 
  Clock, 
  AlertCircle, 
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  X,
  MessageSquare,
  Tag,
  User,
  Calendar,
  ExternalLink,
  FileCode,
  History,
  Send,
  Bot,
  Signal,
  SlidersHorizontal,
  Layout,
  Circle,
  Trash2,
  Palette,
  Search,
  Edit2,
  Save,
  Play,
  ChevronDown,
  ChevronUp,
  Loader2,
  XCircle
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuGroup,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import {
  DndContext,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  useDroppable,
  DragOverlay,
  defaultDropAnimationSideEffects,
  DragStartEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface IssueBoardProps {
  issues: Issue[];
  setIssues: (issues: Issue[]) => void;
  onAddIssue: (status: string) => void;
  onUpdateIssueDetails?: (issueId: string, details: { title: string; description: string; requirements: string; agentId?: string }) => void;
  onRunTask?: (issueId: string) => Promise<void> | void;
}

const DEFAULT_COLUMNS: { id: string; label: string; icon: any; color?: string }[] = [
  { id: 'backlog', label: 'Backlog', icon: Circle },
  { id: 'todo', label: 'Todo', icon: Circle },
  { id: 'in-progress', label: 'In Progress', icon: Circle, color: 'bg-amber-500 text-white' },
  { id: 'review', label: 'In Review', icon: Circle, color: 'bg-green-600 text-white' },
  { id: 'done', label: 'Done', icon: CheckCircle2, color: 'bg-blue-600 text-white' },
];

const COLUMN_COLORS = [
  { name: 'Default', value: '' },
  { name: 'Amber', value: 'bg-amber-500 text-white' },
  { name: 'Green', value: 'bg-green-600 text-white' },
  { name: 'Blue', value: 'bg-blue-600 text-white' },
  { name: 'Rose', value: 'bg-rose-500 text-white' },
  { name: 'Purple', value: 'bg-purple-600 text-white' },
  { name: 'Slate', value: 'bg-slate-700 text-white' },
];

interface SortableIssueCardProps {
  key?: string | number;
  issue: Issue;
  getAgent: (id?: string) => any;
  getPriorityColor: (priority: Issue['priority']) => string;
  onClick?: () => void;
  isOverlay?: boolean;
  displaySettings: {
    showDescription: boolean;
    showPriority: boolean;
    showAgent: boolean;
  };
}

function IssueCard({ issue, getAgent, getPriorityColor, onClick, isOverlay, displaySettings }: SortableIssueCardProps) {
  return (
    <Card 
      onClick={onClick}
      className={cn(
        "shadow-none border-zinc-200/60 hover:border-zinc-300 transition-all cursor-grab active:cursor-grabbing group rounded-lg overflow-hidden bg-white",
        isOverlay && "shadow-lg border-zinc-300 bg-white rotate-1 scale-[1.02] z-50"
      )}
    >
      <CardContent className="p-3.5 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium text-zinc-400 uppercase tracking-wider">
            {issue.id}
          </span>
          {displaySettings.showPriority && (
            <div className={cn(
              "px-1.5 py-0.5 rounded-sm text-[9px] font-bold uppercase tracking-widest",
              issue.priority === 'high' ? "bg-zinc-900 text-white" : 
              issue.priority === 'medium' ? "bg-zinc-100 text-zinc-600 border border-zinc-200" : 
              "bg-zinc-50 text-zinc-400 border border-zinc-100"
            )}>
              {issue.priority}
            </div>
          )}
        </div>
        
        <h4 className="text-[13px] font-semibold leading-snug text-zinc-900 group-hover:text-black transition-colors">
          {issue.title}
        </h4>
        
        {displaySettings.showDescription && (
          <p className="text-[11.5px] text-zinc-500 line-clamp-2 leading-relaxed font-medium">
            {issue.description}
          </p>
        )}

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            {displaySettings.showAgent && issue.agentId && (
              <div className="flex items-center gap-1.5">
                <Avatar className="h-5 w-5 rounded-full border border-zinc-100">
                  <AvatarImage src={getAgent(issue.agentId)?.avatar_url} />
                  <AvatarFallback className="text-[8px] bg-zinc-50 text-zinc-400">{getAgent(issue.agentId)?.name[0]}</AvatarFallback>
                </Avatar>
                <span className="text-[10px] font-medium text-zinc-400 italic">
                  {getAgent(issue.agentId)?.name}
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <MoreHorizontal className="w-3.5 h-3.5 text-zinc-300" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SortableIssueCard({ issue, getAgent, getPriorityColor, onClick, displaySettings }: SortableIssueCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: issue.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <IssueCard issue={issue} getAgent={getAgent} getPriorityColor={getPriorityColor} onClick={onClick} displaySettings={displaySettings} />
    </div>
  );
}

function DroppableColumn({ 
  column, 
  issues, 
  onAddIssue, 
  getAgent, 
  getPriorityColor, 
  onIssueClick,
  onDeleteColumn,
  onChangeColumnColor,
  onRenameColumn,
  displaySettings
}: {
  key?: string | number,
  column: any,
  issues: Issue[],
  onAddIssue: (status: string) => void,
  getAgent: (id?: string) => any,
  getPriorityColor: (priority: Issue['priority']) => string,
  onIssueClick: (issue: Issue) => void,
  onDeleteColumn: (id: string) => void,
  onChangeColumnColor: (id: string, color: string) => void,
  onRenameColumn: (id: string, label: string) => void,
  displaySettings: any
}) {
  const { setNodeRef } = useDroppable({
    id: column.id,
  });

  const [isEditing, setIsEditing] = useState(false);
  const [newLabel, setNewLabel] = useState(column.label);

  const columnIssues = issues.filter(i => i.status === column.id);

  const handleRename = () => {
    if (newLabel.trim()) {
      onRenameColumn(column.id, newLabel);
    }
    setIsEditing(false);
  };

  return (
    <div ref={setNodeRef} className="flex-shrink-0 w-[280px] flex flex-col gap-3 bg-zinc-50/50 rounded-lg p-2.5 h-full border border-zinc-100 shadow-sm overflow-hidden">
      <div className={cn(
        "flex items-center justify-between px-2 py-1.5 rounded-md",
        column.color ? column.color.replace('bg-', 'bg-zinc-900').replace('text-white', 'text-white') : "bg-transparent"
      )}>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className={cn(
            "w-1.5 h-1.5 rounded-full",
            column.id === 'in-progress' ? "bg-amber-400" :
            column.id === 'done' ? "bg-emerald-500" :
            column.id === 'review' ? "bg-blue-500" :
            "bg-zinc-300"
          )} />
          
          {isEditing ? (
            <Input
              autoFocus
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              onBlur={handleRename}
              onKeyDown={(e) => e.key === 'Enter' && handleRename()}
              className="h-6 text-[12px] font-bold bg-white border-zinc-200 px-1.5"
            />
          ) : (
            <h3 
              className="font-bold text-[12px] tracking-tight uppercase text-zinc-900 truncate cursor-pointer hover:opacity-80"
              onClick={() => setIsEditing(true)}
            >
              {column.label}
            </h3>
          )}
          
          <span className="text-[10px] font-bold text-zinc-400 bg-zinc-100/80 px-1.5 py-0.5 rounded-sm shrink-0">
            {columnIssues.length}
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          <DropdownMenu>
            <DropdownMenuTrigger className="p-1 hover:bg-zinc-100 rounded-md transition-colors">
              <MoreHorizontal className="w-3.5 h-3.5 text-zinc-400" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Column Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setIsEditing(true)}>
                  <Edit2 className="w-4 h-4 mr-2" />
                  Rename Column
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="text-[10px] font-semibold text-zinc-500 uppercase py-1">Change Color</DropdownMenuLabel>
                <div className="grid grid-cols-4 gap-1 p-2">
                  {COLUMN_COLORS.map((color) => (
                    <button
                      key={color.name}
                      onClick={() => onChangeColumnColor(column.id, color.value)}
                      className={cn(
                        "w-6 h-6 rounded-full border border-zinc-200",
                        color.value || "bg-white"
                      )}
                      title={color.name}
                    />
                  ))}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  className="text-rose-600 focus:text-rose-600 focus:bg-rose-50"
                  onClick={() => onDeleteColumn(column.id)}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete Column
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
          <button 
            onClick={() => onAddIssue(column.id)}
            className="p-1 hover:bg-zinc-100 rounded-md transition-colors"
          >
            <Plus className="w-3.5 h-3.5 text-zinc-400" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 pr-1.5 custom-scrollbar">
        <div className="space-y-2.5 min-h-[150px] pb-4">
          <SortableContext
            items={columnIssues.map(i => i.id)}
            strategy={verticalListSortingStrategy}
          >
            {columnIssues.map((issue) => (
              <SortableIssueCard 
                key={issue.id} 
                issue={issue} 
                getAgent={getAgent} 
                getPriorityColor={getPriorityColor} 
                onClick={() => onIssueClick(issue)}
                displaySettings={displaySettings}
              />
            ))}
          </SortableContext>
          <button 
            onClick={() => onAddIssue(column.id)}
            className="w-full py-2 flex items-center justify-center gap-2 border border-dashed border-zinc-200 text-[10px] font-bold uppercase tracking-widest text-zinc-400 hover:text-zinc-900 hover:border-zinc-300 hover:bg-zinc-50 rounded-md transition-all group"
          >
            <Plus className="w-3 h-3" />
            Add Task
          </button>
        </div>
      </div>
    </div>
  );
}

export function IssueBoard({ issues, setIssues, onAddIssue, onUpdateIssueDetails, onRunTask }: IssueBoardProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [commentText, setCommentText] = useState('');
  const [panelTab, setPanelTab] = useState('Details');
  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [expandedRuns, setExpandedRuns] = useState<Record<string, boolean>>({});

  const toggleRun = (runId: string) => {
    setExpandedRuns((prev) => ({ ...prev, [runId]: !prev[runId] }));
  };

  const runStatusStyles = (status: string) => {
    switch (status) {
      case 'done':
        return { dot: 'bg-green-500', badge: 'bg-green-500/15 text-green-700 border-green-500/30', label: 'Completed' };
      case 'failed':
        return { dot: 'bg-red-500', badge: 'bg-red-500/15 text-red-700 border-red-500/30', label: 'Failed' };
      case 'running':
      default:
        return { dot: 'bg-yellow-500 animate-pulse', badge: 'bg-yellow-500/15 text-yellow-700 border-yellow-500/30', label: 'Running' };
    }
  };

  const stepStatusStyles = (status: string) => {
    switch (status) {
      case 'done':
        return { icon: <CheckCircle2 className="w-4 h-4 text-green-600" />, text: 'text-foreground line-through decoration-green-600/60' };
      case 'in_progress':
        return { icon: <Loader2 className="w-4 h-4 text-yellow-600 animate-spin" />, text: 'text-foreground font-medium' };
      case 'blocked':
      case 'cancelled':
      case 'failed':
        return { icon: <XCircle className="w-4 h-4 text-red-600" />, text: 'text-muted-foreground line-through' };
      case 'todo':
      default:
        return { icon: <Circle className="w-4 h-4 text-muted-foreground" />, text: 'text-muted-foreground' };
    }
  };

  // Fetch employees
  React.useEffect(() => {
    let mounted = true;
    listEmployees()
      .then((data) => {
        if (mounted) setEmployees(data);
      })
      .catch((e) => console.error("Failed to load employees:", e));
    return () => { mounted = false; };
  }, []);

  // Editable state
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editRequirements, setEditRequirements] = useState('');
  const [editAgentId, setEditAgentId] = useState<string | undefined>('');
  // Baseline snapshot of the last saved values — used to compute the dirty flag.
  const [savedSnapshot, setSavedSnapshot] = useState<{ title: string; description: string; requirements: string; agentId?: string } | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // When the user opens a different issue, initialize edit fields + baseline snapshot.
  const selectedIssueId = selectedIssue?.id;
  React.useEffect(() => {
    if (!selectedIssueId) {
      setSavedSnapshot(null);
      return;
    }
    const fresh = issues.find((i) => i.id === selectedIssueId) || selectedIssue;
    if (!fresh) return;
    setEditTitle(fresh.title || '');
    setEditDescription(fresh.description || '');
    setEditRequirements(fresh.requirements || '');
    setEditAgentId(fresh.agentId);
    setSavedSnapshot({
      title: fresh.title || '',
      description: fresh.description || '',
      requirements: fresh.requirements || '',
      agentId: fresh.agentId,
    });
    // Intentionally only re-runs when the selected id changes — we don't want
    // background polling to clobber the user's in-progress edits.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIssueId]);

  // When the issues list refreshes (polling), keep selectedIssue pointing at
  // the fresh object so the Activity log re-renders with new comments, but do
  // NOT touch the edit field state.
  React.useEffect(() => {
    if (!selectedIssueId) return;
    const fresh = issues.find((i) => i.id === selectedIssueId);
    if (fresh && fresh !== selectedIssue) {
      setSelectedIssue(fresh);
    }
  }, [issues, selectedIssueId]);

  const isDirty = !!selectedIssue && !!savedSnapshot && (
    editTitle !== savedSnapshot.title ||
    editDescription !== savedSnapshot.description ||
    editRequirements !== savedSnapshot.requirements ||
    (editAgentId || '') !== (savedSnapshot.agentId || '')
  );

  const canRun = !!selectedIssue && !!editAgentId && !isDirty && !isRunning;

  const handleSaveDetails = () => {
    if (!selectedIssue) return;

    // Optimistic update — keep the panel open so the user can click Run next.
    const updatedIssue = { ...selectedIssue, title: editTitle, description: editDescription, requirements: editRequirements, agentId: editAgentId };
    setIssues(issues.map(i => i.id === selectedIssue.id ? updatedIssue : i));
    setSelectedIssue(updatedIssue);
    setSavedSnapshot({
      title: editTitle,
      description: editDescription,
      requirements: editRequirements,
      agentId: editAgentId,
    });

    if (onUpdateIssueDetails) {
      onUpdateIssueDetails(selectedIssue.id, {
        title: editTitle,
        description: editDescription,
        requirements: editRequirements,
        agentId: editAgentId
      });
    }
  };

  const handleRunTask = async () => {
    if (!selectedIssue || !canRun || !onRunTask) return;
    setIsRunning(true);
    setPanelTab('Activity');
    try {
      await onRunTask(selectedIssue.id);
    } catch (e) {
      console.error('Failed to run task:', e);
    } finally {
      setIsRunning(false);
    }
  };
  
  const [columns, setColumns] = useState(DEFAULT_COLUMNS);
  const [filterPriority, setFilterPriority] = useState<string | null>(null);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [displaySettings, setDisplaySettings] = useState({
    showDescription: true,
    showPriority: true,
    showAgent: true,
  });

  const handleAddColumn = () => {
    const newId = `col-${Date.now()}`;
    setColumns([...columns, { id: newId, label: 'New Column', icon: Circle }]);
  };

  const handleDeleteColumn = (id: string) => {
    setColumns(columns.filter(c => c.id !== id));
  };

  const handleChangeColumnColor = (id: string, color: string) => {
    setColumns(columns.map(c => c.id === id ? { ...c, color } : c));
  };

  const handleRenameColumn = (id: string, label: string) => {
    setColumns(columns.map(c => c.id === id ? { ...c, label } : c));
  };

  const filteredIssues = issues.filter(issue => {
    const matchesPriority = !filterPriority || issue.priority === filterPriority;
    const matchesAgent = !filterAgent || issue.agentId === filterAgent;
    const matchesSearch = !searchQuery || 
      issue.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      issue.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPriority && matchesAgent && matchesSearch;
  });

  const handleAddComment = () => {
    if (!selectedIssue || !commentText.trim()) return;

    const newComment = {
      id: `comment-${Date.now()}`,
      authorId: 'user-1',
      authorName: 'Hritvik',
      content: commentText,
      timestamp: new Date().toISOString(),
      type: 'user' as const
    };

    const updatedIssues = issues.map(i => 
      i.id === selectedIssue.id 
        ? { ...i, comments: [...(i.comments || []), newComment] }
        : i
    );

    setIssues(updatedIssues);
    setSelectedIssue({ ...selectedIssue, comments: [...(selectedIssue.comments || []), newComment] });
    setCommentText('');
  };
  
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const getAgent = (id?: string) => employees.find(a => a.id === id);

  const getPriorityColor = (priority: Issue['priority']) => {
    switch (priority) {
      case 'high': return 'text-rose-600 bg-rose-50';
      case 'medium': return 'text-amber-600 bg-amber-50';
      case 'low': return 'text-blue-600 bg-blue-50';
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const activeId = active.id;
    const overId = over.id;

    const activeIndex = issues.findIndex((i) => i.id === activeId);
    const draggedIssue = issues[activeIndex];

    // Check if dropped over a column
    const isOverColumn = columns.some(col => col.id === overId);

    if (isOverColumn) {
      if (draggedIssue.status !== overId) {
        const updatedIssues = [...issues];
        updatedIssues[activeIndex] = { ...draggedIssue, status: overId as string };
        setIssues(updatedIssues);
      }
      return;
    }

    // Dropped over another issue
    const overIndex = issues.findIndex((i) => i.id === overId);
    const overIssue = issues[overIndex];

    if (overIssue && activeId !== overId) {
      const updatedIssues = [...issues];
      if (draggedIssue.status !== overIssue.status) {
        updatedIssues[activeIndex] = { ...draggedIssue, status: overIssue.status };
      }
      setIssues(arrayMove(updatedIssues, activeIndex, overIndex));
    }
  };

  const scroll = (direction: 'left' | 'right') => {
    if (scrollContainerRef.current) {
      const scrollAmount = 300;
      scrollContainerRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      });
    }
  };

  const activeIssue = activeId ? issues.find(i => i.id === activeId) : null;

  return (
    <div className="relative group/board h-full flex flex-col gap-6 min-h-0">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 gap-2 text-xs font-bold border-border shadow-sm"
            onClick={handleAddColumn}
          >
            <Plus className="w-3.5 h-3.5" />
            Add Column
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger className={cn(
              buttonVariants({ variant: "ghost", size: "sm" }),
              "h-8 gap-2 text-xs font-medium",
              (filterPriority || filterAgent) ? "text-primary" : "text-muted-foreground hover:text-foreground"
            )}>
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Filter {(filterPriority || filterAgent) ? '(Active)' : ''}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Filter by Priority</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setFilterPriority(null)}>
                  <div className="flex items-center justify-between w-full">
                    <span>All Priorities</span>
                    {!filterPriority && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilterPriority('high')}>
                  <div className="flex items-center justify-between w-full">
                    <span>High</span>
                    {filterPriority === 'high' && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilterPriority('medium')}>
                  <div className="flex items-center justify-between w-full">
                    <span>Medium</span>
                    {filterPriority === 'medium' && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setFilterPriority('low')}>
                  <div className="flex items-center justify-between w-full">
                    <span>Low</span>
                    {filterPriority === 'low' && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </DropdownMenuItem>
                
                <DropdownMenuSeparator />
                <DropdownMenuLabel>Filter by Agent</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setFilterAgent(null)}>
                  <div className="flex items-center justify-between w-full">
                    <span>All Agents</span>
                    {!filterAgent && <CheckCircle2 className="w-3 h-3" />}
                  </div>
                </DropdownMenuItem>
                {employees.map(agent => (
                  <DropdownMenuItem key={agent.id} onClick={() => setFilterAgent(agent.id)}>
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-4 w-4">
                          <AvatarImage src={agent.avatar_url} />
                          <AvatarFallback className="text-[6px]">{agent.name[0]}</AvatarFallback>
                        </Avatar>
                        <span>{agent.name}</span>
                      </div>
                      {filterAgent === agent.id && <CheckCircle2 className="w-3 h-3" />}
                    </div>
                  </DropdownMenuItem>
                ))}

                <DropdownMenuSeparator />
                <div className="p-2">
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                    <Input 
                      placeholder="Search issues..." 
                      className="h-8 pl-8 text-xs"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger className={cn(
              buttonVariants({ variant: "ghost", size: "sm" }),
              "h-8 gap-2 text-xs font-medium text-muted-foreground hover:text-foreground"
            )}>
              <Layout className="w-3.5 h-3.5" />
              Display
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuGroup>
                <DropdownMenuLabel>Display Settings</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setDisplaySettings(prev => ({ ...prev, showDescription: !prev.showDescription }))}>
                  <div className="flex items-center justify-between w-full">
                    <span>Show Description</span>
                    {displaySettings.showDescription && <CheckCircle2 className="w-3.5 h-3.5 text-primary" />}
                  </div>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setDisplaySettings(prev => ({ ...prev, showPriority: !prev.showPriority }))}>
                  <div className="flex items-center justify-between w-full">
                    <span>Show Priority</span>
                    {displaySettings.showPriority && <CheckCircle2 className="w-3.5 h-3.5 text-primary" />}
                  </div>
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setDisplaySettings(prev => ({ ...prev, showAgent: !prev.showAgent }))}>
                  <div className="flex items-center justify-between w-full">
                    <span>Show Agent</span>
                    {displaySettings.showAgent && <CheckCircle2 className="w-3.5 h-3.5 text-primary" />}
                  </div>
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        <div className="flex gap-1 opacity-0 group-hover/board:opacity-100 transition-opacity">
          <button 
            onClick={() => scroll('left')}
            className="p-1.5 bg-background border border-border rounded-md hover:bg-secondary transition-colors shadow-sm"
          >
            <ChevronLeft className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button 
            onClick={() => scroll('right')}
            className="p-1.5 bg-background border border-border rounded-md hover:bg-secondary transition-colors shadow-sm"
          >
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
        </div>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div 
          ref={scrollContainerRef}
          className="flex gap-3 h-full overflow-x-auto pb-4 scrollbar-hide no-scrollbar"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {columns.map((column) => (
            <DroppableColumn 
              key={column.id}
              column={column}
              issues={filteredIssues}
              onAddIssue={onAddIssue}
              getAgent={getAgent}
              getPriorityColor={getPriorityColor}
              onIssueClick={setSelectedIssue}
              onDeleteColumn={handleDeleteColumn}
              onChangeColumnColor={handleChangeColumnColor}
              onRenameColumn={handleRenameColumn}
              displaySettings={displaySettings}
            />
          ))}
        </div>

        <DragOverlay dropAnimation={{
          sideEffects: defaultDropAnimationSideEffects({
            styles: {
              active: {
                opacity: '0.5',
              },
            },
          }),
        }}>
          {activeIssue ? (
            <IssueCard 
              issue={activeIssue} 
              getAgent={getAgent} 
              getPriorityColor={getPriorityColor} 
              isOverlay
              displaySettings={displaySettings}
            />
          ) : null}
        </DragOverlay>
      </DndContext>

      <AnimatePresence>
        {selectedIssue && (
          <div className="fixed inset-0 z-50 flex justify-end p-4 sm:p-6 lg:p-8 pointer-events-none">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={() => setSelectedIssue(null)}
              className="absolute inset-0 bg-background/80 backdrop-blur-sm pointer-events-auto"
              style={{
                backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
                backgroundSize: '24px 24px'
              }}
            />
            <motion.div
              initial={{ opacity: 0, x: 50, scale: 0.98 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 50, scale: 0.98 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="relative w-full max-w-lg h-full bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden pointer-events-auto"
            >
              {/* Header / Tabs Area */}
              <div className="flex items-center justify-between p-4 border-b border-border bg-background shrink-0">
                <div className="flex items-center gap-4">
                  <div className="flex items-center bg-muted/50 p-1 rounded-full border border-border/50">
                    {['Details', 'Activity'].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setPanelTab(tab)}
                        className={cn(
                          "px-4 py-1.5 text-sm font-medium rounded-full transition-all",
                          panelTab === tab 
                            ? "bg-background text-foreground shadow-sm" 
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={() => {
                      if (confirm("Delete this task?")) {
                        // TODO: handle delete
                        setSelectedIssue(null);
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    onClick={() => setSelectedIssue(null)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto overflow-x-hidden bg-muted/20 min-w-0 w-full custom-scrollbar">
                <div className="w-full">
                  {panelTab === "Details" && (
                    <div className="p-6 space-y-6">
                      <div className="space-y-3">
                        <Label className="text-sm font-medium text-muted-foreground">Task Title</Label>
                        <Input 
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="bg-background border-border shadow-sm h-11 text-base font-semibold"
                          placeholder="Task Title"
                        />
                      </div>

                      <div className="space-y-3">
                        <Label className="text-sm font-medium text-muted-foreground">Description</Label>
                        <Textarea 
                          value={editDescription}
                          onChange={(e) => setEditDescription(e.target.value)}
                          className="bg-background border-border shadow-sm resize-none min-h-[100px]"
                          placeholder="Add a detailed description..."
                        />
                      </div>
                      
                      <div className="space-y-3">
                        <Label className="text-sm font-medium text-muted-foreground">Requirements</Label>
                        <Textarea 
                          value={editRequirements}
                          onChange={(e) => setEditRequirements(e.target.value)}
                          className="bg-background border-border shadow-sm resize-none min-h-[100px]"
                          placeholder="Add acceptance criteria and requirements..."
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-3">
                          <Label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                            <Bot className="h-3 w-3" /> Agent Lead
                          </Label>
                          <Select 
                            value={editAgentId || "unassigned"} 
                            onValueChange={(val) => setEditAgentId(val === "unassigned" ? undefined : val)}
                          >
                            <SelectTrigger className="w-full bg-background border-border shadow-sm h-[42px]">
                              <SelectValue placeholder="Select Agent">
                                <div className="flex items-center gap-2.5">
                                  <Avatar className="h-6 w-6">
                                    <AvatarImage src={getAgent(editAgentId)?.avatar_url} />
                                    <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">{getAgent(editAgentId)?.name?.[0] || '?'}</AvatarFallback>
                                  </Avatar>
                                  <span className="text-sm font-medium text-foreground">{getAgent(editAgentId)?.name || 'Unassigned'}</span>
                                </div>
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="unassigned">
                                <div className="flex items-center gap-2.5">
                                  <Avatar className="h-6 w-6">
                                    <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">?</AvatarFallback>
                                  </Avatar>
                                  <span className="text-sm font-medium text-foreground">Unassigned</span>
                                </div>
                              </SelectItem>
                              {employees.map(agent => (
                                <SelectItem key={agent.id} value={agent.id}>
                                  <div className="flex items-center gap-2.5">
                                    <Avatar className="h-6 w-6">
                                      <AvatarImage src={agent.avatar_url} />
                                      <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">{agent.name[0]}</AvatarFallback>
                                    </Avatar>
                                    <span className="text-sm font-medium text-foreground">{agent.name}</span>
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-3">
                          <Label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                            <User className="h-3 w-3" /> User Assigned
                          </Label>
                          <div className="flex items-center gap-2.5 bg-background p-3 rounded-lg border border-border shadow-sm">
                            <Avatar className="h-6 w-6">
                              <AvatarImage src="https://api.dicebear.com/7.x/avataaars/svg?seed=hritvik" />
                              <AvatarFallback className="bg-muted text-[10px] text-muted-foreground">H</AvatarFallback>
                            </Avatar>
                            <span className="text-sm font-medium text-foreground">Hritvik</span>
                          </div>
                        </div>
                      </div>

                      {selectedIssue.fileChanges && selectedIssue.fileChanges.length > 0 && (
                        <div className="space-y-3">
                          <Label className="text-sm font-medium text-muted-foreground">Artifacts</Label>
                          <div className="grid grid-cols-1 gap-2">
                            {selectedIssue.fileChanges.map(file => (
                              <div key={file} className="flex items-center gap-3 text-xs text-foreground bg-background px-3 py-2 rounded-lg border border-border font-mono shadow-sm">
                                <FileCode className="w-4 h-4 text-muted-foreground" />
                                {file}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {panelTab === "Activity" && (
                    <div className="p-4 sm:p-5 w-full min-w-0">
                      <div className="space-y-4">
                        {(!selectedIssue.runs || selectedIssue.runs.length === 0) ? (
                          <div className="flex flex-col items-center justify-center py-12 text-center space-y-2 bg-background border border-dashed border-border/60 rounded-xl w-full">
                            <History className="h-8 w-8 text-muted-foreground/50" />
                            <p className="text-sm font-medium text-foreground">No Runs Yet</p>
                            <p className="text-xs text-muted-foreground">Each time you run this task, a new run card will appear here.</p>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {selectedIssue.runs.map((run, idx) => {
                              const rs = runStatusStyles(run.status);
                              const isLatest = idx === 0;
                              const isExpanded = expandedRuns[run.id] ?? isLatest;
                              const doneCount = run.steps.filter((s) => s.status === 'done').length;
                              return (
                                <div
                                  key={run.id}
                                  className="rounded-xl border border-border bg-background shadow-sm overflow-hidden"
                                >
                                  <button
                                    type="button"
                                    onClick={() => toggleRun(run.id)}
                                    className="w-full flex items-center justify-between gap-3 px-4 py-3 hover:bg-muted/40 transition-colors text-left"
                                  >
                                    <div className="flex items-center gap-3 min-w-0 flex-1">
                                      <span className={cn("w-2.5 h-2.5 rounded-full shrink-0", rs.dot)} />
                                      <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span className="text-sm font-semibold text-foreground truncate">
                                            Run {run.id.replace(/^sprun_/, '')}
                                          </span>
                                          <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-full border", rs.badge)}>
                                            {rs.label}
                                          </span>
                                          {run.employeeName && (
                                            <span className="text-[11px] text-muted-foreground truncate">· {run.employeeName}</span>
                                          )}
                                        </div>
                                        <div className="text-[11px] text-muted-foreground mt-0.5">
                                          {new Date(run.createdAt).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                                          {run.steps.length > 0 && ` · ${doneCount}/${run.steps.length} steps`}
                                        </div>
                                      </div>
                                    </div>
                                    {isExpanded ? (
                                      <ChevronUp className="w-4 h-4 text-muted-foreground shrink-0" />
                                    ) : (
                                      <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                                    )}
                                  </button>
                                  {isExpanded && (
                                    <div className="px-4 pb-4 pt-1 space-y-2 border-t border-border/60 bg-muted/20">
                                      {run.steps.length === 0 ? (
                                        <div className="text-xs text-muted-foreground italic py-3">
                                          Agent is planning the work…
                                        </div>
                                      ) : (
                                        <ul className="space-y-1.5 pt-2">
                                          {run.steps.map((step) => {
                                            const ss = stepStatusStyles(step.status);
                                            return (
                                              <li
                                                key={step.id}
                                                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-background border border-border/50"
                                              >
                                                <span className="shrink-0">{ss.icon}</span>
                                                <span className={cn("text-sm flex-1 break-words", ss.text)}>
                                                  {step.title || step.id}
                                                </span>
                                              </li>
                                            );
                                          })}
                                        </ul>
                                      )}
                                      {run.summary && run.status === 'done' && (
                                        <div className="mt-3 text-xs leading-relaxed text-foreground bg-background border border-border/50 rounded-lg p-3 whitespace-pre-wrap break-words">
                                          {run.summary}
                                        </div>
                                      )}
                                      {run.error && run.status === 'failed' && (
                                        <div className="mt-3 text-xs leading-relaxed text-red-700 bg-red-500/10 border border-red-500/30 rounded-lg p-3 whitespace-pre-wrap break-words">
                                          {run.error}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-border bg-background flex items-center justify-end gap-3 shadow-[0_-4px_10px_-5px_rgba(0,0,0,0.05)] shrink-0">
                <Button variant="outline" onClick={() => setSelectedIssue(null)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveDetails}
                  className="gap-2 px-6"
                >
                  <Save className="w-4 h-4" /> Save Details
                </Button>
                <Button
                  onClick={handleRunTask}
                  disabled={!canRun}
                  className="gap-2 px-6"
                  title={
                    !editAgentId
                      ? 'Assign an employee first'
                      : isDirty
                        ? 'Save your changes before running'
                        : isRunning
                          ? 'Task is already running'
                          : 'Run this task with the assigned employee'
                  }
                >
                  <Play className="w-4 h-4" /> {isRunning ? 'Running…' : 'Run'}
                </Button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
      
      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #e4e4e7;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #d4d4d8;
        }
      `}} />
    </div>
  );
}
