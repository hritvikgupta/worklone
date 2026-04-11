import React, { useRef, useState } from 'react';
import { Issue, IssueStatus } from '@/src/types';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import { MOCK_AGENTS } from '@/src/constants';
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
  Edit2
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
        "shadow-sm border border-border/60 hover:border-primary/30 transition-all cursor-grab active:cursor-grabbing group rounded-lg overflow-hidden bg-white",
        isOverlay && "shadow-xl border-primary/20 bg-background rotate-2 scale-105"
      )}
    >
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono text-muted-foreground/70 uppercase tracking-tight">
            {issue.id}
          </span>
        </div>
        
        <h4 className="text-[13px] font-bold leading-tight text-foreground/90 group-hover:text-primary transition-colors">
          {issue.title}
        </h4>
        
        {displaySettings.showDescription && (
          <p className="text-[12px] text-muted-foreground/80 line-clamp-2 leading-relaxed">
            {issue.description}
          </p>
        )}

        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2">
            {displaySettings.showAgent && issue.agentId && (
              <Avatar className="h-5 w-5 rounded-full border border-border/50">
                <AvatarImage src={getAgent(issue.agentId)?.avatar} />
                <AvatarFallback className="text-[8px] bg-secondary">{getAgent(issue.agentId)?.name[0]}</AvatarFallback>
              </Avatar>
            )}
            {displaySettings.showPriority && (
              <div className={cn(
                "flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider",
                issue.priority === 'high' ? "bg-rose-100 text-rose-700" : 
                issue.priority === 'medium' ? "bg-amber-100 text-amber-700" : 
                "bg-blue-100 text-blue-700"
              )}>
                <Signal className="w-2.5 h-2.5" />
                {issue.priority}
              </div>
            )}
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
    <div ref={setNodeRef} className="flex-shrink-0 w-80 flex flex-col gap-4 bg-secondary/10 rounded-xl p-2 min-h-[500px]">
      <div className={cn(
        "flex items-center justify-between px-3 py-2 rounded-lg",
        column.color || "bg-transparent"
      )}>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {column.icon && <column.icon className={cn("w-4 h-4", !column.color && "text-muted-foreground/50")} />}
          {!column.icon && <Circle className={cn("w-4 h-4", !column.color && "text-muted-foreground/50")} />}
          
          {isEditing ? (
            <Input
              autoFocus
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              onBlur={handleRename}
              onKeyDown={(e) => e.key === 'Enter' && handleRename()}
              className="h-6 text-[13px] font-bold bg-white/20 border-none focus-visible:ring-1 focus-visible:ring-white/50 px-1"
            />
          ) : (
            <h3 
              className="font-bold text-[13px] tracking-tight truncate cursor-pointer hover:opacity-80"
              onClick={() => setIsEditing(true)}
            >
              {column.label}
            </h3>
          )}
          
          <span className={cn(
            "text-[11px] font-bold px-1.5 py-0.5 rounded-full shrink-0",
            column.color ? "bg-white/20" : "bg-secondary text-muted-foreground"
          )}>
            {columnIssues.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger className="p-1 hover:bg-black/5 rounded transition-colors">
              <MoreHorizontal className="w-4 h-4" />
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
                <DropdownMenuLabel className="text-[10px] font-semibold text-muted-foreground uppercase py-1">Change Color</DropdownMenuLabel>
                <div className="grid grid-cols-4 gap-1 p-2">
                  {COLUMN_COLORS.map((color) => (
                    <button
                      key={color.name}
                      onClick={() => onChangeColumnColor(column.id, color.value)}
                      className={cn(
                        "w-6 h-6 rounded-full border border-border",
                        color.value || "bg-white"
                      )}
                      title={color.name}
                    />
                  ))}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem 
                  className="text-destructive focus:text-destructive"
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
            className="p-1 hover:bg-black/5 rounded transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-3 pr-2 min-h-[150px] pb-4">
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
            className="w-full py-1.5 flex items-center gap-2 px-2 text-[11px] text-muted-foreground hover:bg-secondary/50 rounded-md transition-colors group"
          >
            <Plus className="w-3 h-3 opacity-50 group-hover:opacity-100" />
            New
          </button>
        </div>
      </ScrollArea>
    </div>
  );
}

export function IssueBoard({ issues, setIssues, onAddIssue }: IssueBoardProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [commentText, setCommentText] = useState('');
  
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

  const getAgent = (id?: string) => MOCK_AGENTS.find(a => a.id === id);

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
    <div className="relative group/board h-full flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="h-8 gap-2 text-xs font-bold border-border/60 shadow-sm"
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
                {MOCK_AGENTS.map(agent => (
                  <DropdownMenuItem key={agent.id} onClick={() => setFilterAgent(agent.id)}>
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <Avatar className="h-4 w-4">
                          <AvatarImage src={agent.avatar} />
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
            className="p-1.5 bg-background border border-border/50 rounded-md hover:bg-secondary transition-colors shadow-sm"
          >
            <ChevronLeft className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button 
            onClick={() => scroll('right')}
            className="p-1.5 bg-background border border-border/50 rounded-md hover:bg-secondary transition-colors shadow-sm"
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
          className="flex gap-6 h-full overflow-x-auto pb-4 scrollbar-hide no-scrollbar"
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
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedIssue(null)}
              className="fixed inset-0 bg-background/40 backdrop-blur-[2px] z-40"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 h-full w-full max-w-xl bg-background border-l border-border shadow-2xl z-50 flex flex-col"
            >
              <div className="flex items-center justify-between p-4 border-b border-border/50">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-muted-foreground">{selectedIssue.id}</span>
                  <Badge variant="outline" className="text-[10px] uppercase tracking-wider">{selectedIssue.status}</Badge>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 w-8 p-0"
                    onClick={() => setSelectedIssue(null)}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <ScrollArea className="flex-1">
                <div className="p-8 space-y-8">
                  <div className="space-y-4">
                    <h2 className="text-2xl font-semibold tracking-tight leading-tight">
                      {selectedIssue.title}
                    </h2>
                    <div className="flex flex-wrap gap-2">
                      {selectedIssue.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="text-[10px] font-medium">#{tag}</Badge>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-6 py-6 border-y border-border/50">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        <Bot className="w-3 h-3" />
                        Agent
                      </div>
                      <div className="flex items-center gap-2">
                        <Avatar className="h-6 w-6 rounded-sm">
                          <AvatarImage src={getAgent(selectedIssue.agentId)?.avatar} />
                          <AvatarFallback className="rounded-sm text-[10px]">{getAgent(selectedIssue.agentId)?.name[0]}</AvatarFallback>
                        </Avatar>
                        <span className="text-sm font-medium">{getAgent(selectedIssue.agentId)?.name || 'Unassigned'}</span>
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        <User className="w-3 h-3" />
                        Assignee
                      </div>
                      <div className="flex items-center gap-2">
                        <Avatar className="h-6 w-6 rounded-sm">
                          <AvatarImage src="https://api.dicebear.com/7.x/avataaars/svg?seed=hritvik" />
                          <AvatarFallback className="rounded-sm text-[10px]">H</AvatarFallback>
                        </Avatar>
                        <span className="text-sm font-medium">Hritvik</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold flex items-center gap-2">
                        <Clock className="w-4 h-4 text-muted-foreground" />
                        Task Description
                      </h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {selectedIssue.description}
                      </p>
                    </div>

                    {selectedIssue.fileChanges && selectedIssue.fileChanges.length > 0 && (
                      <div className="space-y-3">
                        <h3 className="text-sm font-semibold flex items-center gap-2">
                          <FileCode className="w-4 h-4 text-muted-foreground" />
                          File Changes
                        </h3>
                        <div className="space-y-1.5">
                          {selectedIssue.fileChanges.map(file => (
                            <div key={file} className="flex items-center gap-2 text-xs text-foreground/80 bg-secondary/30 px-2 py-1 rounded border border-border/50 font-mono">
                              <FileCode className="w-3 h-3 opacity-50" />
                              {file}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-sm font-semibold flex items-center gap-2">
                      <History className="w-4 h-4 text-muted-foreground" />
                      Agent Process
                    </h3>
                    <div className="space-y-6 relative before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-border/50">
                      {[...(selectedIssue.comments || [])].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()).map((item) => (
                        <div key={item.id} className="flex gap-4 relative">
                          <div className={cn(
                            "w-6 h-6 rounded-full flex-shrink-0 z-10 flex items-center justify-center border border-background shadow-sm",
                            item.type === 'agent' ? "bg-primary text-primary-foreground" : "bg-secondary"
                          )}>
                            {item.type === 'agent' ? <Bot className="w-3 h-3" /> : <User className="w-3 h-3" />}
                          </div>
                          <div className="space-y-1 flex-1">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold">{item.authorName}</span>
                              <span className="text-[10px] text-muted-foreground">
                                {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                            <div className={cn(
                              "text-sm p-3 rounded-lg border",
                              item.type === 'agent' ? "bg-secondary/20 border-border/50" : "bg-background border-border"
                            )}>
                              {item.content}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </ScrollArea>

              <div className="p-4 border-t border-border/50 bg-secondary/10">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                    placeholder="Add a comment for the agent..."
                    className="flex-1 h-9 bg-background border border-border rounded-md px-3 text-xs focus:outline-none focus:ring-1 focus:ring-primary/30"
                  />
                  <Button size="sm" onClick={handleAddComment}>
                    <Send className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
      
      <style dangerouslySetInnerHTML={{ __html: `
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}} />
    </div>
  );
}
