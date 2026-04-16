import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Plus,
  Users,
  Search,
  Briefcase,
  Calendar,
  X,
  Check,
  Trash2,
  Activity,
  Folder,
  FileText,
  ChevronRight,
  File,
  MessageSquare,
  Send,
  Sparkles,
  Paperclip,
  Mic,
  Settings2,
  GitFork,
  ArrowRight,
  Radio,
  GripVertical
} from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { motion, AnimatePresence } from 'motion/react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import * as TeamAPI from '@/src/api/teams';
import { listEmployees, EmployeeDetail } from '@/src/api/employees';
import { getMarkdownTree, MarkdownTreeNode } from '@/lib/api';

// --- TYPES ---
export interface TeamMember {
  id: string;
  name: string;
  role: string;
  avatar?: string;
  task?: string;
}

export interface TeamEdge {
  from: string;
  to: string;
}

export interface Team {
  id: string;
  name: string;
  goal: string;
  topology: string;
  projectType: string;
  deadline: string;
  members: TeamMember[];
  attachedFiles: string[];
  edges: TeamEdge[];
  sequenceOrder: string[];
  broadcasterId: string;
  createdAt: string;
}

interface FileItem {
  id: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileItem[];
}

function mapMarkdownNodesToFileItems(nodes: MarkdownTreeNode[]): FileItem[] {
  return nodes.map(node => ({
    id: node.path,
    name: node.name,
    type: node.type,
    children: node.children ? mapMarkdownNodesToFileItems(node.children) : undefined,
  }));
}

// --- INITIAL DATA ---
const MOCK_FILES: FileItem[] = [
  {
    id: 'f1',
    name: 'project-assets',
    type: 'folder',
    children: [
      { id: 'f1-1', name: 'logo.svg', type: 'file' },
      { id: 'f1-2', name: 'brand-guide.pdf', type: 'file' },
    ],
  },
  {
    id: 'f2',
    name: 'documentation',
    type: 'folder',
    children: [
      { id: 'f2-1', name: 'roadmap.md', type: 'file' },
      { id: 'f2-2', name: 'api-specs.yaml', type: 'file' },
      {
        id: 'f2-3',
        name: 'internal',
        type: 'folder',
        children: [{ id: 'f2-3-1', name: 'budget.xlsx', type: 'file' }],
      },
    ],
  },
  { id: 'f3', name: 'readme.md', type: 'file' },
  { id: 'f4', name: 'package.json', type: 'file' },
];

const projectTypeColors: Record<string, string> = {
  development: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  design: "bg-pink-500/10 text-pink-500 border-pink-500/20",
  marketing: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  research: "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
  operations: "bg-slate-500/10 text-slate-500 border-slate-500/20",
};

const statusColors: Record<string, string> = {
  working: "bg-emerald-500",
  idle: "bg-amber-500",
  blocked: "bg-red-500",
  offline: "bg-slate-500",
};

// --- FILE TREE COMPONENT ---
function FileTree({ 
  items, 
  selectedFiles, 
  onToggle 
}: { 
  items: FileItem[]; 
  selectedFiles: string[]; 
  onToggle: (id: string) => void 
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-1">
      {items.map(item => (
        <div key={item.id}>
          <div 
            onClick={() => item.type === 'file' && onToggle(item.id)}
            className={cn(
              "flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-colors group",
              item.type === 'file' && selectedFiles.includes(item.id) 
                ? "bg-primary/10 text-primary font-medium" 
                : "hover:bg-muted/50 text-foreground"
            )}
          >
            {item.type === 'folder' && (
              <button 
                onClick={(e) => toggleExpand(e, item.id)}
                className="p-0.5 hover:bg-muted rounded transition-transform"
                style={{ transform: expanded[item.id] ? 'rotate(90deg)' : 'none' }}
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
            {item.type === 'folder' ? (
              <Folder className={cn("w-4 h-4", expanded[item.id] ? "text-blue-500 fill-blue-500/20" : "text-blue-400")} />
            ) : (
              <div className={cn(
                "flex h-4 w-4 items-center justify-center rounded border",
                selectedFiles.includes(item.id) 
                  ? "bg-primary border-primary text-primary-foreground" 
                  : "border-border"
              )}>
                {selectedFiles.includes(item.id) ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <FileText className="h-3 w-3 text-muted-foreground/50" />
                )}
              </div>
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
      ))}
    </div>
  );
}

// --- TOPOLOGY CONFIG COMPONENT ---
interface SortableMemberProps {
  member: { id: string; name: string; role: string; avatar?: string; task?: string };
  index: number;
  total: number;
  onTaskChange?: (id: string, task: string) => void;
}

function SortableMember({ member, index, total, onTaskChange }: SortableMemberProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: member.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "flex flex-col gap-2 p-3 rounded-lg border transition-all",
        isDragging 
          ? "bg-background border-primary shadow-lg ring-1 ring-primary/20 scale-[1.02]" 
          : "bg-muted/20 border-border/40"
      )}
    >
      <div className="flex items-center gap-3">
        <div 
          {...attributes} 
          {...listeners}
          className="cursor-grab active:cursor-grabbing p-1 -ml-1 rounded hover:bg-muted/50 text-muted-foreground/40 hover:text-muted-foreground transition-colors"
        >
          <GripVertical className="h-3.5 w-3.5" />
        </div>
        <span className="text-[11px] font-black text-muted-foreground/50 w-5 text-center">
          {index + 1}
        </span>
        <Avatar className="h-6 w-6">
          <AvatarImage src={member.avatar} />
          <AvatarFallback className="text-[10px]">{member.name[0]}</AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-foreground truncate">{member.name}</p>
          <p className="text-[10px] text-muted-foreground truncate">{member.role}</p>
        </div>
        {index < total - 1 && (
          <ArrowRight className="h-3 w-3 text-primary/40 shrink-0" />
        )}
      </div>
      {onTaskChange && (
        <div className="pl-12 pr-6">
          <Input
            placeholder={`Task for ${member.name}...`}
            value={member.task || ""}
            onChange={(e) => onTaskChange(member.id, e.target.value)}
            className="h-8 text-xs bg-background/50 border-border/50"
          />
        </div>
      )}
      {!onTaskChange && member.task && (
        <div className="pl-12 pr-6">
          <p className="text-xs text-muted-foreground italic">Task: {member.task}</p>
        </div>
      )}
    </div>
  );
}

interface TopologyConfigProps {
  topology: string;
  members: { id: string; name: string; role: string; avatar?: string; task?: string }[];
  edges: TeamEdge[];
  onEdgesChange: (edges: TeamEdge[]) => void;
  sequenceOrder: string[];
  onSequenceOrderChange: (order: string[]) => void;
  broadcasterId: string;
  onBroadcasterChange: (id: string) => void;
  onMemberTaskChange?: (id: string, task: string) => void;
}

function TopologyConfig({
  topology,
  members,
  edges,
  onEdgesChange,
  sequenceOrder,
  onSequenceOrderChange,
  broadcasterId,
  onBroadcasterChange,
  onMemberTaskChange,
}: TopologyConfigProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Sync sequenceOrder with members
  useEffect(() => {
    const memberIds = members.map(m => m.id);
    const missingIds = memberIds.filter(id => !sequenceOrder.includes(id));
    const extraIds = sequenceOrder.filter(id => !memberIds.includes(id));

    if (missingIds.length > 0 || extraIds.length > 0) {
      const newOrder = [
        ...sequenceOrder.filter(id => memberIds.includes(id)),
        ...missingIds
      ];
      onSequenceOrderChange(newOrder);
    }
  }, [members, sequenceOrder, onSequenceOrderChange]);

  if (members.length < 2) {
    return (
      <div className="mt-3 rounded-xl border border-dashed border-border/60 bg-muted/20 py-4 text-center">
        <p className="text-[11px] text-muted-foreground">Add at least 2 members to configure connections.</p>
      </div>
    );
  }

  const toggleEdge = (from: string, to: string) => {
    const exists = edges.some(e => e.from === from && e.to === to);
    if (exists) {
      onEdgesChange(edges.filter(e => !(e.from === from && e.to === to)));
    } else {
      onEdgesChange([...edges, { from, to }]);
    }
  };

  const getMember = (id: string) => members.find(m => m.id === id);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = sequenceOrder.indexOf(active.id as string);
      const newIndex = sequenceOrder.indexOf(over.id as string);
      onSequenceOrderChange(arrayMove(sequenceOrder, oldIndex, newIndex));
    }
  };

  if (topology === 'graph') {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="mt-3 rounded-xl border border-border/60 bg-background overflow-hidden"
      >
        <div className="px-4 py-2.5 border-b border-border/50 bg-muted/30">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Define Connections — who can message whom
          </p>
        </div>
        <div className="p-3 space-y-1">
          {members.map(sender => (
            <div key={sender.id} className="flex items-center gap-3 py-2 border-b border-border/30 last:border-0">
              <div className="flex items-center gap-2 w-28 shrink-0">
                <Avatar className="h-6 w-6">
                  <AvatarImage src={sender.avatar} />
                  <AvatarFallback className="text-[10px]">{sender.name[0]}</AvatarFallback>
                </Avatar>
                <span className="text-xs font-medium text-foreground truncate">{sender.name}</span>
              </div>
              <ArrowRight className="h-3 w-3 text-muted-foreground/40 shrink-0" />
              <div className="flex flex-wrap gap-1.5">
                {members.filter(m => m.id !== sender.id).map(target => {
                  const active = edges.some(e => e.from === sender.id && e.to === target.id);
                  return (
                    <button
                      key={target.id}
                      type="button"
                      onClick={() => toggleEdge(sender.id, target.id)}
                      className={cn(
                        "flex items-center gap-1 px-2 py-1 rounded-lg border text-[10px] font-medium transition-all",
                        active
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border/60 text-muted-foreground hover:border-primary/40 hover:text-foreground"
                      )}
                    >
                      {active && <Check className="h-2.5 w-2.5" />}
                      {target.name}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    );
  }

  if (topology === 'sequential') {
    const ordered = sequenceOrder
      .map(id => getMember(id))
      .filter(Boolean) as typeof members;
    // Append any members not yet in the order (visually)
    members.forEach(m => {
      if (!sequenceOrder.includes(m.id)) {
        ordered.push(m);
      }
    });

    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="mt-3 rounded-xl border border-border/60 bg-background overflow-hidden"
      >
        <div className="px-4 py-2.5 border-b border-border/50 bg-muted/30">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Set Order — agents work step by step
          </p>
        </div>
        <div className="p-3">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={ordered.map(m => m.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-1.5">
                {ordered.map((member, idx) => (
                  <SortableMember
                    key={member.id}
                    member={member}
                    index={idx}
                    total={ordered.length}
                    onTaskChange={onMemberTaskChange}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      </motion.div>
    );
  }

  if (topology === 'broadcast') {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="mt-3 rounded-xl border border-border/60 bg-background overflow-hidden"
      >
        <div className="px-4 py-2.5 border-b border-border/50 bg-muted/30">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            Select Broadcaster — sends to all others
          </p>
        </div>
        <div className="p-3 space-y-1">
          {members.map(member => {
            const isSelected = broadcasterId === member.id;
            return (
              <button
                key={member.id}
                type="button"
                onClick={() => onBroadcasterChange(member.id)}
                className={cn(
                  "w-full flex items-center gap-3 p-2.5 rounded-lg border text-left transition-all",
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-border/40 hover:border-primary/40 hover:bg-muted/30"
                )}
              >
                <div className={cn(
                  "h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-all",
                  isSelected ? "border-primary bg-primary" : "border-border"
                )}>
                  {isSelected && <div className="h-1.5 w-1.5 rounded-full bg-white" />}
                </div>
                <Avatar className="h-7 w-7">
                  <AvatarImage src={member.avatar} />
                  <AvatarFallback className="text-[10px]">{member.name[0]}</AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate">{member.name}</p>
                  <p className="text-[10px] text-muted-foreground truncate">{member.role}</p>
                </div>
                {isSelected && (
                  <Badge className="text-[9px] px-1.5 py-0 bg-primary/10 text-primary border-primary/20 shrink-0">
                    Broadcaster
                  </Badge>
                )}
                {!isSelected && (
                  <Badge variant="outline" className="text-[9px] px-1.5 py-0 text-muted-foreground shrink-0">
                    Receiver
                  </Badge>
                )}
              </button>
            );
          })}
        </div>
      </motion.div>
    );
  }

  return null;
}

// --- TEAM CARD COMPONENT ---
function TeamCard({ team, onConfigure, onChat, onRun, isRunning }: {
  team: Team;
  onConfigure: () => void;
  onChat: () => void;
  onRun: () => void;
  isRunning?: boolean;
}) {
  return (
    <Card 
      className="group relative flex flex-col h-full transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1.5 flex-1 min-w-0">
            <h3 className="font-semibold text-foreground leading-none truncate">{team.name}</h3>
            <p className="text-xs text-muted-foreground line-clamp-2 mt-1.5 leading-relaxed">
              {team.goal}
            </p>
          </div>
          {team.projectType && (
            <Badge
              variant="outline"
              className={cn("shrink-0", projectTypeColors[team.projectType] || "")}
            >
              {team.projectType}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 space-y-4">
        <div className="flex items-center gap-4 text-[11px] font-medium text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" />
            <span>{team.members.length} members</span>
          </div>
          {team.deadline && (
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              <span>{new Date(team.deadline).toLocaleDateString()}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between">
          <div className="flex -space-x-2">
            {team.members.slice(0, 5).map((member) => (
              <Avatar
                key={member.id}
                className="h-8 w-8 border-2 border-card shadow-sm"
              >
                <AvatarImage src={member.avatar} alt={member.name} />
                <AvatarFallback className="bg-secondary text-[10px] font-bold text-secondary-foreground uppercase">
                  {member.name.split(" ").map((n) => n[0]).join("")}
                </AvatarFallback>
              </Avatar>
            ))}
            {team.members.length > 5 && (
              <div className="flex h-8 w-8 items-center justify-center rounded-full border-2 border-card bg-muted text-[10px] font-black text-muted-foreground uppercase">
                +{team.members.length - 5}
              </div>
            )}
          </div>
        </div>

        {team.members.length > 0 && team.members.some((m) => m.task) && (
          <div className="border-t border-border/50 pt-3 mt-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/60 mb-2">Active Tasks</p>
            <div className="space-y-1.5">
              {team.members
                .filter((m) => m.task)
                .slice(0, 2)
                .map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center gap-2 text-xs"
                  >
                    <div className="h-1 w-1 rounded-full bg-primary/30 shrink-0" />
                    <span className="text-muted-foreground truncate">
                      <strong className="font-semibold text-foreground">{member.name}:</strong> {member.task}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-4 border-t border-border/50 bg-muted/5 mt-auto">
        <div className="flex w-full gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 h-8 text-[10px] font-bold uppercase tracking-wider bg-background hover:bg-muted transition-all active:scale-[0.98] shadow-sm"
            onClick={(e) => { e.stopPropagation(); onConfigure(); }}
          >
            <Settings2 className="w-3 h-3 mr-2 text-muted-foreground" />
            Configure
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 h-8 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all active:scale-[0.98]"
            onClick={(e) => { e.stopPropagation(); onChat(); }}
          >
            <MessageSquare className="w-3 h-3 mr-2" />
            Chat
          </Button>
          <Button
            size="sm"
            disabled={isRunning || team.members.length === 0}
            className={cn(
              "flex-1 h-8 text-[10px] font-bold uppercase tracking-wider shadow-sm transition-all active:scale-[0.98]",
              isRunning && "opacity-70"
            )}
            onClick={(e) => { e.stopPropagation(); onRun(); }}
          >
            {isRunning ? (
              <>
                <span className="h-2 w-2 rounded-full bg-primary-foreground animate-pulse mr-2" />
                Running
              </>
            ) : (
              <>
                <Sparkles className="w-3 h-3 mr-2" />
                Run
              </>
            )}
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}

// --- TEAM DETAILS SLIDE-OVER PANEL ---
function TeamDetailsPanel({
  team,
  employees,
  agentFiles,
  initialTab,
  onClose,
  onUpdate,
  onDelete
}: {
  team: Team | null;
  employees: EmployeeDetail[];
  agentFiles: FileItem[];
  initialTab?: string | null;
  onClose: () => void;
  onUpdate: (team: Team) => void;
  onDelete: (id: string) => void;
}) {
  const [activeTab, setActiveTab] = useState("Configure");

  // Jump to a specific tab when requested (e.g. after Run)
  useEffect(() => {
    if (initialTab && team) {
      setActiveTab(initialTab);
    }
  }, [initialTab, team?.id]);

  // Edit State
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [topology, setTopology] = useState("graph");
  const [projectType, setProjectType] = useState("");
  const [customType, setCustomType] = useState("");
  const [deadline, setDeadline] = useState("");
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  // Topology config state
  const [edges, setEdges] = useState<TeamEdge[]>([]);
  const [sequenceOrder, setSequenceOrder] = useState<string[]>([]);
  const [broadcasterId, setBroadcasterId] = useState("");
  const [memberTasks, setMemberTasks] = useState<Record<string, string>>({});
  // Activity tab — live run monitoring
  const [runs, setRuns] = useState<import('@/src/api/teams').TeamRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const standardTypes = ["development", "design", "marketing", "research", "operations"];

  // Sync state when team changes
  useEffect(() => {
    if (team) {
      setName(team.name);
      setGoal(team.goal);
      setTopology(team.topology || "graph");

      if (standardTypes.includes(team.projectType)) {
        setProjectType(team.projectType);
        setCustomType("");
      } else {
        setProjectType("custom");
        setCustomType(team.projectType);
      }

      setDeadline(team.deadline);
      const memberIds = team.members.map(m => m.id);
      setSelectedAgentIds(memberIds);
      setSelectedFileIds(team.attachedFiles || []);
      setEdges(team.edges || []);
      setSequenceOrder(team.sequenceOrder?.length ? team.sequenceOrder : memberIds);
      setBroadcasterId(team.broadcasterId || memberIds[0] || "");
      
      const initialTasks: Record<string, string> = {};
      team.members.forEach(m => {
        initialTasks[m.id] = m.task || "";
      });
      setMemberTasks(initialTasks);
      
      setActiveTab("Configure");
    }
  }, [team]);

  // Poll runs when Activity tab is open
  useEffect(() => {
    const fetchRuns = async () => {
      if (!team) return;
      try {
        setRunsLoading(true);
        const data = await TeamAPI.listRuns(team.id);
        setRuns(data);
      } catch (e) {
        // silent
      } finally {
        setRunsLoading(false);
      }
    };

    if (activeTab === "Activity" && team) {
      fetchRuns();
      pollRef.current = setInterval(fetchRuns, 4000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [activeTab, team?.id]);

  const updateMemberTask = (employeeId: string, task: string) => {
    setMemberTasks(prev => ({ ...prev, [employeeId]: task }));
  };

  const handleSave = () => {
    if (!team) return;

    const updatedMembers: TeamMember[] = employees
      .filter(a => selectedAgentIds.includes(a.id))
      .map(a => {
        return {
          id: a.id,
          name: a.name,
          role: a.role,
          avatar: a.avatar_url,
          task: memberTasks[a.id] || ""
        };
      });

    onUpdate({
      ...team,
      name,
      goal,
      topology,
      projectType: projectType === "custom" ? customType : projectType,
      deadline,
      members: updatedMembers,
      attachedFiles: selectedFileIds,
      edges,
      sequenceOrder,
      broadcasterId,
    });
    
    onClose();
  };

  const filteredAgents = employees.filter(a => 
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleAgent = (id: string) => {
    setSelectedAgentIds(prev => 
      prev.includes(id) ? prev.filter(aid => aid !== id) : [...prev, id]
    );
  };

  const toggleFile = (id: string) => {
    setSelectedFileIds(prev => 
      prev.includes(id) ? prev.filter(fid => fid !== id) : [...prev, id]
    );
  };

  return (
    <AnimatePresence>
      {team && (
        <div className="fixed inset-0 z-50 flex justify-end p-4 sm:p-6 lg:p-8">
          {/* Backdrop with dotted grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
            onClick={onClose}
          />

          {/* Floating Slide-over Panel (Right Aligned) */}
          <motion.div
            initial={{ opacity: 0, x: 50, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.98 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="relative w-full max-w-lg h-full bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header / Tabs Area */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-background">
              <div className="flex items-center gap-4">
                <div className="flex items-center bg-muted/50 p-1 rounded-full border border-border/50">
                  {['Configure', 'Members', 'Memory', 'Activity'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        "px-4 py-1.5 text-sm font-medium rounded-full transition-all",
                        activeTab === tab 
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
                    if (confirm("Delete this team?")) {
                      onDelete(team.id);
                      onClose();
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={onClose}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden bg-muted/20 min-w-0 w-full">
              <div className="w-full">
                {activeTab === "Configure" && (
                  <div className="p-6 space-y-6">
                    <div className="space-y-3">
                      <Label className="text-sm font-medium text-muted-foreground">Team Name</Label>
                      <Input
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="bg-background border-border shadow-sm h-11"
                      />
                    </div>

                    <div className="space-y-3">
                      <Label className="text-sm font-medium text-muted-foreground">Goal / Instruction</Label>
                      <Textarea
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        rows={4}
                        className="bg-background border-border shadow-sm resize-none"
                        placeholder="Update unit instructions and goals"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <Label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                          <Briefcase className="h-3 w-3" /> Type
                        </Label>
                        <div className="space-y-2">
                          <Select value={projectType} onValueChange={setProjectType}>
                            <SelectTrigger className="bg-background border-border h-10 shadow-sm">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="development">Development</SelectItem>
                              <SelectItem value="design">Design</SelectItem>
                              <SelectItem value="marketing">Marketing</SelectItem>
                              <SelectItem value="research">Research</SelectItem>
                              <SelectItem value="operations">Operations</SelectItem>
                              <SelectItem value="custom" className="text-primary font-medium">
                                <div className="flex items-center gap-2">
                                  <Plus className="w-3 h-3" />
                                  Custom Type
                                </div>
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          {projectType === "custom" && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              className="pt-1"
                            >
                              <Input
                                placeholder="Enter unit type..."
                                value={customType}
                                onChange={(e) => setCustomType(e.target.value)}
                                className="h-9 text-xs bg-background border-primary/20 focus-visible:ring-primary/20 shadow-inner"
                              />
                            </motion.div>
                          )}
                        </div>
                      </div>
                      <div className="space-y-3">
                        <Label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                          <Calendar className="h-3 w-3" /> Deadline
                        </Label>
                        <Input
                          type="date"
                          value={deadline}
                          onChange={(e) => setDeadline(e.target.value)}
                          className="bg-background border-border h-10 shadow-sm"
                        />
                      </div>
                    </div>

                    {/* Topology Selector */}
                    <div className="space-y-3">
                      <Label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                        <GitFork className="h-3 w-3" /> Agent Topology
                      </Label>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { value: 'graph', icon: GitFork, label: 'Graph', desc: 'Any agent talks to any other' },
                          { value: 'sequential', icon: ArrowRight, label: 'Sequential', desc: 'Agents work in order A→B→C' },
                          { value: 'broadcast', icon: Radio, label: 'Broadcast', desc: 'One agent sends to all' },
                        ].map(({ value, icon: Icon, label, desc }) => (
                          <button
                            key={value}
                            type="button"
                            onClick={() => setTopology(value)}
                            className={cn(
                              "flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all",
                              topology === value
                                ? "border-primary bg-primary/5 text-primary shadow-sm"
                                : "border-border bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
                            )}
                          >
                            <Icon className="h-4 w-4" />
                            <span className="text-[11px] font-bold uppercase tracking-wider leading-none">{label}</span>
                            <span className="text-[10px] leading-snug opacity-70">{desc}</span>
                          </button>
                        ))}
                      </div>
                      <AnimatePresence mode="wait">
                        <TopologyConfig
                          key={topology}
                          topology={topology}
                          members={employees.filter(a => selectedAgentIds.includes(a.id)).map(a => ({ id: a.id, name: a.name, role: a.role, avatar: a.avatar_url, task: memberTasks[a.id] || "" }))}
                          edges={edges}
                          onEdgesChange={setEdges}
                          sequenceOrder={sequenceOrder}
                          onSequenceOrderChange={setSequenceOrder}
                          broadcasterId={broadcasterId}
                          onBroadcasterChange={setBroadcasterId}
                          onMemberTaskChange={updateMemberTask}
                        />
                      </AnimatePresence>
                    </div>
                  </div>
                )}

                {activeTab === "Members" && (
                  <div className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-medium text-foreground">Manage Roster</Label>
                      <Badge variant="outline" className="bg-background">{selectedAgentIds.length} Agents</Badge>
                    </div>

                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="Search employees..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 bg-background border-border shadow-sm"
                      />
                    </div>

                    <div className="border border-border rounded-xl bg-background overflow-hidden">
                      <ScrollArea className="h-[400px]">
                        <div className="p-2 space-y-1">
                          {filteredAgents.map((agent) => (
                            <div
                              key={agent.id}
                              className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                              onClick={() => toggleAgent(agent.id)}
                            >
                              <div className={cn(
                                "flex h-4 w-4 items-center justify-center rounded border",
                                selectedAgentIds.includes(agent.id) 
                                  ? "bg-primary border-primary text-primary-foreground" 
                                  : "border-border"
                              )}>
                                {selectedAgentIds.includes(agent.id) && <Check className="h-3 w-3" />}
                              </div>
                              <div className="relative">
                                <Avatar className="h-9 w-9">
                                  <AvatarImage src={agent.avatar_url} />
                                  <AvatarFallback>{agent.name[0]}</AvatarFallback>
                                </Avatar>
                                <span className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background ${statusColors[agent.status || 'offline']}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">{agent.name}</p>
                                <p className="text-xs text-muted-foreground truncate">{agent.role}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </ScrollArea>
                    </div>
                  </div>
                )}

                {activeTab === "Memory" && (
                  <div className="p-6 space-y-6">
                    <div className="flex items-center justify-between">
                       <div>
                          <h3 className="text-lg font-semibold text-foreground">Attach Knowledge</h3>
                          <p className="text-xs text-muted-foreground">Select files to index into memory.</p>
                       </div>
                       <Badge variant="outline" className="bg-background">{selectedFileIds.length} Files</Badge>
                    </div>

                    <div className="border border-border rounded-xl bg-background overflow-hidden shadow-sm">
                      <ScrollArea className="h-[450px] p-4">
                        <FileTree
                          items={agentFiles}
                          selectedFiles={selectedFileIds}
                          onToggle={toggleFile}
                        />                      </ScrollArea>
                    </div>
                  </div>
                )}

                {activeTab === "Activity" && (
                  <div className="p-4 sm:p-6 bg-muted/5 space-y-4 w-full max-w-full box-border overflow-x-hidden">
                    <div className="flex items-center justify-between gap-2">
                      <Label className="text-sm font-medium text-muted-foreground shrink-0">Team Runs</Label>
                      {runsLoading && (
                        <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground shrink-0">
                          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                          Live
                        </span>
                      )}
                    </div>
                    <div className="space-y-3 w-full">
                      {runs.length > 0 ? (
                        runs.map(run => (
                          <div key={run.id} className="flex flex-col gap-2 bg-background p-4 rounded-xl border border-border shadow-sm w-full min-w-0 overflow-hidden">
                            {/* Run header */}
                            <div className="flex items-start justify-between gap-2 w-full min-w-0">
                              <div className="flex items-center gap-2 min-w-0 flex-1">
                                <Activity className={cn("h-4 w-4 shrink-0", run.status === "running" ? "text-blue-500" : "text-primary")} />
                                <span className="text-sm font-medium text-foreground truncate min-w-0 flex-1">{run.goal || "No goal"}</span>
                              </div>
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-[10px] uppercase tracking-wider shrink-0",
                                  run.status === "completed" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                                  run.status === "failed" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                                  run.status === "running" ? "bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse" :
                                  "bg-muted/50 text-muted-foreground"
                                )}
                              >
                                {run.status}
                              </Badge>
                            </div>
                            {/* Timestamps */}
                            <div className="flex items-center gap-3 text-[10px] text-muted-foreground min-w-0 overflow-hidden">
                              <span className="truncate">Started {new Date(run.created_at).toLocaleString()}</span>
                              {run.completed_at && <span className="truncate shrink-0">· Done {new Date(run.completed_at).toLocaleString()}</span>}
                            </div>
                            {/* Member statuses */}
                            {run.members && run.members.length > 0 && (
                              <div className="mt-2 pt-3 border-t border-border/50 space-y-2 w-full min-w-0">
                                {run.members.map(rm => (
                                  <div key={rm.employee_id} className="flex items-start gap-2 bg-muted/20 p-2.5 rounded-lg border border-border/40 w-full min-w-0 overflow-hidden">
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-1.5 min-w-0">
                                        <p className="text-xs font-semibold text-foreground truncate flex-1 min-w-0">{rm.employee_name}</p>
                                        <span className="text-[10px] text-muted-foreground truncate shrink-0">· {rm.employee_role}</span>
                                      </div>
                                      <p className="text-[10px] text-muted-foreground mt-0.5 truncate w-full">{rm.assigned_task}</p>
                                      {rm.result && (
                                        <div
                                          className="mt-2 p-3 bg-background border border-border/50 rounded-lg text-xs text-foreground cursor-pointer hover:bg-muted/50 transition-colors line-clamp-3 w-full break-all overflow-hidden [&_p]:my-1 [&_ul]:my-1 [&_ul]:pl-4 [&_ul]:list-disc [&_ol]:my-1 [&_ol]:pl-4 [&_ol]:list-decimal"
                                          onClick={() => setSelectedResult(rm.result)}
                                          title="Click to view full output"
                                        >
                                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {rm.result}
                                          </ReactMarkdown>
                                        </div>
                                      )}                                    </div>
                                    <Badge
                                      variant="outline"
                                      className={cn("text-[9px] mt-0.5 shrink-0 uppercase tracking-wider",
                                        rm.task_status === "done" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                                        rm.task_status === "blocked" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                                        rm.task_status === "in_progress" ? "bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse" :
                                        ""
                                      )}
                                    >
                                      {rm.task_status === "in_progress" ? "Working" : rm.task_status}
                                    </Badge>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="flex flex-col items-center justify-center py-12 text-center space-y-2 bg-background border border-dashed border-border/60 rounded-xl w-full">
                          <Activity className="h-6 w-6 text-muted-foreground/30" />
                          <p className="text-xs text-muted-foreground">No runs yet</p>
                          <p className="text-[10px] text-muted-foreground/60">Click <strong>Run</strong> on the team card to start.</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-border bg-background flex items-center justify-end gap-3 shadow-[0_-4px_10px_-5px_rgba(0,0,0,0.05)]">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={!name.trim() || selectedAgentIds.length === 0}
                className="gap-2 px-6"
              >
                Save Changes
              </Button>
            </div>
          </motion.div>
        </div>
      )}
      <Dialog open={!!selectedResult} onOpenChange={(open) => !open && setSelectedResult(null)}>
        <DialogContent className="sm:max-w-3xl w-[95vw] max-h-[85vh] flex flex-col overflow-hidden">
          <DialogHeader className="shrink-0">
            <DialogTitle>Agent Output</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto mt-4 p-4 rounded-md border bg-muted/30 min-w-0">
            <div 
              className="text-sm leading-relaxed break-words whitespace-pre-wrap overflow-hidden w-full [&_p]:my-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_pre]:my-4 [&_pre]:p-4 [&_pre]:bg-background [&_pre]:border [&_pre]:border-border/50 [&_pre]:rounded-lg [&_pre]:overflow-x-auto [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {selectedResult || ""}
              </ReactMarkdown>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </AnimatePresence>
  );
}

// --- TEAM CHAT SLIDE-OVER PANEL ---
function TeamChatPanel({ team, onClose }: { team: Team | null; onClose: () => void }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (team) {
      setMessages([
        { role: 'assistant', content: `Hello! I am the synchronized intelligence for **${team.name}**. How can I help the unit today?` }
      ]);
    }
  }, [team]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput("");

    // Simulate response
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: `Acknowledged. I'm processing that for the ${team?.name} roster. I've indexed the associated knowledge files to assist with your request.` }]);
    }, 800);
  };

  return (
    <AnimatePresence>
      {team && (
        <div className="fixed inset-0 z-50 flex justify-end p-4 sm:p-6 lg:p-8">
          {/* Backdrop with dotted grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
            onClick={onClose}
          />

          {/* Floating Chat Panel (Right Aligned) */}
          <motion.div
            initial={{ opacity: 0, x: 50, scale: 0.98 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 50, scale: 0.98 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="relative w-full max-w-xl h-full bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-background">
              <div className="flex items-center gap-3">
                 <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
                    <MessageSquare className="w-5 h-5 text-primary-foreground" />
                 </div>
                 <div>
                    <h2 className="text-sm font-bold text-foreground truncate max-w-[200px] uppercase tracking-wider">{team.name} / Sync</h2>
                    <div className="flex items-center gap-1.5 mt-0.5">
                       <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                       <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">Active Intelligence</p>
                    </div>
                 </div>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-muted-foreground hover:text-foreground"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Message Area */}
            <ScrollArea className="flex-1 p-6 bg-muted/20" ref={scrollRef}>
              <div className="space-y-6">
                 {messages.map((msg, i) => (
                   <div key={i} className={cn(
                     "flex flex-col gap-2 max-w-[85%]",
                     msg.role === 'user' ? "ml-auto items-end" : "items-start"
                   )}>
                      <div className="flex items-center gap-2 px-1">
                         <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                            {msg.role === 'user' ? 'You' : 'Unit Mind'}
                         </span>
                      </div>
                      <div className={cn(
                        "p-4 rounded-2xl text-sm leading-relaxed shadow-sm border",
                        msg.role === 'user' 
                          ? "bg-primary text-primary-foreground border-primary/20 rounded-tr-none" 
                          : "bg-background text-foreground border-border rounded-tl-none"
                      )}>
                        {msg.content}
                      </div>
                   </div>
                 ))}
              </div>
            </ScrollArea>

            {/* Input Area */}
            <div className="p-6 border-t border-border bg-background">
               <div className="relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-primary/20 to-primary/10 rounded-2xl blur opacity-25 group-focus-within:opacity-50 transition duration-1000" />
                  <div className="relative bg-background border border-border rounded-xl p-3 shadow-sm focus-within:border-primary/50 transition-all">
                    <textarea
                      placeholder={`Message ${team.name} roster...`}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSend();
                        }
                      }}
                      className="w-full bg-transparent border-none focus:ring-0 outline-none focus:outline-none shadow-none resize-none text-sm min-h-[60px] py-1 text-foreground placeholder:text-muted-foreground/60"
                    />
                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/50">
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                          <Paperclip className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                          <Mic className="w-4 h-4" />
                        </Button>
                      </div>
                      <Button 
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="h-8 px-4 rounded-lg flex items-center gap-2 transition-all active:scale-95 shadow-md shadow-primary/10"
                      >
                        <span className="text-[10px] font-bold uppercase tracking-widest">Send</span>
                        <Send className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
               </div>
               <div className="mt-3 flex items-center justify-center gap-4 text-[10px] text-muted-foreground font-medium uppercase tracking-widest">
                  <span className="flex items-center gap-1"><Sparkles className="w-3 h-3 text-primary" /> Multi-Agent Context</span>
                  <div className="w-1 h-1 rounded-full bg-border" />
                  <span>Shift + Enter for new line</span>
               </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// --- CREATE TEAM MODAL (STYLED LIKE SCREENSHOT) ---
interface CreateTeamModalProps {
  open: boolean;
  employees: EmployeeDetail[];
  agentFiles: FileItem[];
  onOpenChange: (open: boolean) => void;
  onCreateTeam: (team: Omit<Team, "id" | "createdAt">) => void;
}

function CreateTeamModal({
  open,
  employees,
  agentFiles,
  onOpenChange,
  onCreateTeam,
}: CreateTeamModalProps) {
  const [teamName, setTeamName] = useState("");
  const [teamGoal, setTeamGoal] = useState("");
  const [topology, setTopology] = useState("graph");
  const [projectType, setProjectType] = useState("");
  const [customType, setCustomType] = useState("");
  const [deadline, setDeadline] = useState("");
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<string[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([]);
  const [memberTasks, setMemberTasks] = useState<Record<string, string>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("Configure");
  // Topology config state
  const [edges, setEdges] = useState<TeamEdge[]>([]);
  const [sequenceOrder, setSequenceOrder] = useState<string[]>([]);
  const [broadcasterId, setBroadcasterId] = useState("");

  const filteredEmployees = employees.filter(
    (emp) =>
      emp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      emp.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedEmployees = employees.filter((emp) =>
    selectedEmployeeIds.includes(emp.id)
  );

  const toggleEmployee = (id: string) => {
    setSelectedEmployeeIds((prev) =>
      prev.includes(id)
        ? prev.filter((empId) => empId !== id)
        : [...prev, id]
    );
  };

  const toggleFile = (id: string) => {
    setSelectedFileIds(prev => 
      prev.includes(id) 
        ? prev.filter(fid => fid !== id) 
        : [...prev, id]
    );
  };

  const updateMemberTask = (employeeId: string, task: string) => {
    setMemberTasks((prev) => ({
      ...prev,
      [employeeId]: task,
    }));
  };

  const handleSubmit = () => {
    if (!teamName.trim() || selectedEmployeeIds.length === 0) return;

    const members: TeamMember[] = selectedEmployees.map((emp) => ({
      id: emp.id,
      name: emp.name,
      role: emp.role,
      avatar: emp.avatar_url,
      task: memberTasks[emp.id] || "",
    }));

    onCreateTeam({
      name: teamName,
      goal: teamGoal,
      topology,
      projectType: projectType === "custom" ? customType : projectType,
      deadline,
      members,
      attachedFiles: selectedFileIds,
      edges,
      sequenceOrder,
      broadcasterId,
    });

    resetForm();
    onOpenChange(false);
  };

  const resetForm = () => {
    setTeamName("");
    setTeamGoal("");
    setTopology("graph");
    setProjectType("");
    setCustomType("");
    setDeadline("");
    setSelectedEmployeeIds([]);
    setSelectedFileIds([]);
    setMemberTasks({});
    setSearchQuery("");
    setActiveTab("Configure");
    setEdges([]);
    setSequenceOrder([]);
    setBroadcasterId("");
  };

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) resetForm();
    onOpenChange(isOpen);
  };

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 lg:p-8">
          {/* Backdrop with dotted grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
            style={{
              backgroundImage: 'radial-gradient(circle, var(--border) 1px, transparent 1px)',
              backgroundSize: '24px 24px'
            }}
            onClick={() => handleOpenChange(false)}
          />

          {/* Floating Card Modal (Centered) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="relative w-full max-w-3xl max-h-[90vh] bg-background rounded-2xl border border-border shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Header / Tabs Area */}
            <div className="flex items-center justify-between p-4 border-b border-border bg-background">
              <div className="flex items-center gap-4">
                <div className="flex items-center bg-muted/50 p-1 rounded-full border border-border/50">
                  {['Configure', 'Memory'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        "px-4 py-1.5 text-sm font-medium rounded-full transition-all",
                        activeTab === tab 
                          ? "bg-background text-foreground shadow-sm" 
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
                <div className="h-6 w-px bg-border mx-2" />
                <Avatar className="h-8 w-8">
                  <AvatarImage src="https://api.dicebear.com/7.x/avataaars/svg?seed=team" />
                  <AvatarFallback>T</AvatarFallback>
                </Avatar>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                  <Trash2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={() => handleOpenChange(false)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Scrollable Form Content */}
            <ScrollArea className="flex-1 overflow-y-auto bg-muted/20">
              <div className="flex flex-col">
                {activeTab === 'Configure' ? (
                  <>
                    {/* Name Section */}
                    <div className="p-6 border-b border-border/50 space-y-3">
                      <Label className="text-sm font-medium text-muted-foreground">Team Name</Label>
                      <Input
                        placeholder="e.g. Hiring Manager Team"
                        value={teamName}
                        onChange={(e) => setTeamName(e.target.value)}
                        className="bg-background border-border/60 shadow-sm h-11"
                      />
                    </div>

                    {/* Goal / Instruction Section */}
                    <div className="p-6 border-b border-border/50 space-y-3">
                      <Label className="text-sm font-medium text-muted-foreground">Goal / Instruction</Label>
                      <Textarea
                        placeholder="Define the specific instructions and goals for this unit"
                        value={teamGoal}
                        onChange={(e) => setTeamGoal(e.target.value)}
                        rows={3}
                        className="bg-background border-border/60 shadow-sm resize-none"
                      />
                    </div>

                    {/* Project Details Section */}
                    <div className="p-6 border-b border-border/50 bg-background space-y-6">
                      <Label className="text-sm font-medium text-muted-foreground block">Project Settings</Label>
                      <div className="grid gap-6 sm:grid-cols-2">
                        <div className="space-y-3">
                          <Label className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                            <Briefcase className="h-3.5 w-3.5" />
                            Type
                          </Label>
                          <div className="space-y-2">
                            <Select value={projectType} onValueChange={setProjectType}>
                              <SelectTrigger className="bg-background border-border/60 shadow-sm h-10">
                                <SelectValue placeholder="Select type" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="development">Development</SelectItem>
                                <SelectItem value="design">Design</SelectItem>
                                <SelectItem value="marketing">Marketing</SelectItem>
                                <SelectItem value="research">Research</SelectItem>
                                <SelectItem value="operations">Operations</SelectItem>
                                <SelectItem value="custom" className="text-primary font-medium">
                                  <div className="flex items-center gap-2">
                                    <Plus className="w-3 h-3" />
                                    Custom Type
                                  </div>
                                </SelectItem>
                              </SelectContent>
                            </Select>
                            {projectType === "custom" && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="pt-1"
                              >
                                <Input
                                  placeholder="Enter custom unit type..."
                                  value={customType}
                                  onChange={(e) => setCustomType(e.target.value)}
                                  className="h-9 text-xs bg-background border-primary/20 focus-visible:ring-primary/20 shadow-inner"
                                />
                              </motion.div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-3">
                          <Label className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                            <Calendar className="h-3.5 w-3.5" />
                            Deadline
                          </Label>
                          <Input
                            type="date"
                            value={deadline}
                            onChange={(e) => setDeadline(e.target.value)}
                            className="bg-background border-border/60 shadow-sm h-10"
                          />
                        </div>
                      </div>

                      {/* Topology Selector */}
                      <div className="space-y-3">
                        <Label className="text-xs font-medium text-muted-foreground flex items-center gap-2">
                          <GitFork className="h-3.5 w-3.5" />
                          Agent Topology
                        </Label>
                        <div className="grid grid-cols-3 gap-3">
                          {[
                            { value: 'graph', icon: GitFork, label: 'Graph', desc: 'Any agent talks to any other' },
                            { value: 'sequential', icon: ArrowRight, label: 'Sequential', desc: 'Agents work in order A→B→C' },
                            { value: 'broadcast', icon: Radio, label: 'Broadcast', desc: 'One agent sends to all' },
                          ].map(({ value, icon: Icon, label, desc }) => (
                            <button
                              key={value}
                              type="button"
                              onClick={() => setTopology(value)}
                              className={cn(
                                "flex flex-col items-center gap-2 p-3 rounded-xl border text-center transition-all",
                                topology === value
                                  ? "border-primary bg-primary/5 text-primary shadow-sm"
                                  : "border-border/60 bg-background text-muted-foreground hover:border-primary/40 hover:text-foreground"
                              )}
                            >
                              <Icon className="h-4 w-4" />
                              <span className="text-[11px] font-bold uppercase tracking-wider leading-none">{label}</span>
                              <span className="text-[10px] leading-snug opacity-70">{desc}</span>
                            </button>
                          ))}
                        </div>
                        <AnimatePresence mode="wait">
                          <TopologyConfig
                            key={topology}
                            topology={topology}
                            members={employees.filter(a => selectedEmployeeIds.includes(a.id)).map(a => ({ id: a.id, name: a.name, role: a.role, avatar: a.avatar_url, task: memberTasks[a.id] || "" }))}
                            edges={edges}
                            onEdgesChange={setEdges}
                            sequenceOrder={sequenceOrder}
                            onSequenceOrderChange={setSequenceOrder}
                            broadcasterId={broadcasterId}
                            onBroadcasterChange={setBroadcasterId}
                            onMemberTaskChange={updateMemberTask}
                          />
                        </AnimatePresence>
                      </div>
                    </div>

                    {/* Members Section */}
                    <div className="p-6 bg-muted/10">
                      <div className="flex items-center justify-between mb-4">
                        <Label className="text-sm font-medium text-muted-foreground">Team Members</Label>
                        <Badge variant="outline" className="bg-background">{selectedEmployeeIds.length} Selected</Badge>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="relative">
                          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            placeholder="Search employees..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-9 bg-background border-border/60 shadow-sm"
                          />
                        </div>

                        <div className="border border-border/60 rounded-xl bg-background overflow-hidden">
                          <ScrollArea className="h-[240px]">
                            <div className="p-2 space-y-1">
                              {filteredEmployees.map((employee) => (
                                <div
                                  key={employee.id}
                                  className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                                  onClick={() => toggleEmployee(employee.id)}
                                >
                                  <div className={cn(
                                    "flex h-4 w-4 items-center justify-center rounded border",
                                    selectedEmployeeIds.includes(employee.id) 
                                      ? "bg-primary border-primary text-primary-foreground" 
                                      : "border-border"
                                  )}>
                                    {selectedEmployeeIds.includes(employee.id) && <Check className="h-3 w-3" />}
                                  </div>
                                  <div className="relative">
                                    <Avatar className="h-9 w-9 border border-border/50">
                                      <AvatarImage src={employee.avatar_url} alt={employee.name} />
                                      <AvatarFallback className="bg-secondary text-xs">
                                        {employee.name.split(" ").map((n) => n[0]).join("")}
                                      </AvatarFallback>
                                    </Avatar>
                                    <span className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-background ${statusColors[employee.status || 'offline']}`} />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-foreground truncate">{employee.name}</p>
                                    <p className="text-xs text-muted-foreground truncate">{employee.role}</p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </ScrollArea>
                        </div>

                        {selectedEmployees.length > 0 && (
                          <div className="space-y-3 pt-4">
                            <Label className="text-sm font-medium text-muted-foreground">Assign Tasks</Label>
                            <div className="space-y-2">
                              {selectedEmployees.map((employee) => (
                                <div key={employee.id} className="flex items-center gap-3 bg-background p-2 rounded-lg border border-border/60 shadow-sm">
                                  <Avatar className="h-7 w-7 flex-shrink-0">
                                    <AvatarImage src={employee.avatar_url} />
                                    <AvatarFallback className="bg-secondary text-xs">{employee.name[0]}</AvatarFallback>
                                  </Avatar>
                                  <Input
                                    placeholder={`Task for ${employee.name}...`}
                                    value={memberTasks[employee.id] || ""}
                                    onChange={(e) => updateMemberTask(employee.id, e.target.value)}
                                    className="flex-1 border-none shadow-none focus-visible:ring-0 px-0 h-8"
                                  />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-8">
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-foreground">Attach Knowledge</h3>
                      <p className="text-sm text-muted-foreground">Select files and folders to index into this team's memory.</p>
                    </div>

                    <div className="border border-border/60 rounded-2xl bg-background overflow-hidden shadow-sm">
                      <div className="p-4 border-b border-border bg-muted/30 flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Agent Files Browser</span>
                        <Badge variant="secondary" className="bg-primary/10 text-primary border-none">{selectedFileIds.length} Selected</Badge>
                      </div>
                      <ScrollArea className="h-[400px] p-4">
                        <FileTree
                          items={agentFiles}
                          selectedFiles={selectedFileIds}
                          onToggle={toggleFile}
                        />                      </ScrollArea>
                    </div>

                    {selectedFileIds.length > 0 && (
                      <div className="mt-6 p-4 rounded-xl border border-primary/20 bg-primary/5">
                        <Label className="text-xs font-bold uppercase tracking-widest text-primary mb-2 block">Attached to Team Memory</Label>
                        <div className="flex flex-wrap gap-2">
                          {selectedFileIds.map(fid => (
                            <Badge key={fid} variant="secondary" className="gap-1.5 px-2 py-1 bg-background border-border">
                              <FileText className="w-3 h-3 text-muted-foreground" />
                              {fid}.md
                              <button onClick={() => toggleFile(fid)} className="hover:text-destructive">
                                <X className="w-3 h-3" />
                              </button>
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Footer */}
            <div className="p-4 border-t border-border bg-background flex items-center justify-end gap-3">
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!teamName.trim() || selectedEmployeeIds.length === 0}
                className="gap-2 px-6"
              >
                <Users className="h-4 w-4" />
                Create Team
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// --- MAIN PAGE COMPONENT ---
export function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [agentFiles, setAgentFiles] = useState<FileItem[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [activeChatTeam, setActiveChatTeam] = useState<Team | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningTeamIds, setRunningTeamIds] = useState<Set<string>>(new Set());
  const [openTabOnSelect, setOpenTabOnSelect] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [teamsData, employeesData, treeData] = await Promise.all([
          TeamAPI.listTeams(),
          listEmployees(),
          getMarkdownTree('agent').catch(() => [])
        ]);
        setTeams(teamsData);
        setEmployees(employeesData);
        setAgentFiles(mapMarkdownNodesToFileItems(treeData));
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load data");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleCreateTeam = async (teamData: Omit<Team, "id" | "createdAt">) => {
    try {
      const createdTeam = await TeamAPI.createTeam(teamData);
      setTeams((prev) => [createdTeam, ...prev]);
    } catch (err: any) {
      console.error("Failed to create team:", err);
      // Optional fallback logic if you want to keep local state working when API fails
    }
  };

  const handleUpdateTeam = async (updatedTeam: Team) => {
    try {
      const result = await TeamAPI.updateTeam(updatedTeam.id, updatedTeam);
      setTeams(prev => prev.map(t => t.id === updatedTeam.id ? result : t));
    } catch (err: any) {
      console.error("Failed to update team:", err);
    }
  };

  const handleDeleteTeam = async (id: string) => {
    try {
      await TeamAPI.deleteTeam(id);
      setTeams(prev => prev.filter(t => t.id !== id));
    } catch (err: any) {
      console.error("Failed to delete team:", err);
    }
  };

  const handleRunTeam = async (team: Team) => {
    if (runningTeamIds.has(team.id)) return;
    if (team.members.length === 0) return;

    // Build member_tasks from each member's saved task, fallback to team goal
    const memberTasks: Record<string, string> = {};
    team.members.forEach(m => {
      // m.id === employee_id (set by backend _member_to_dict)
      memberTasks[m.id] = m.task || team.goal || "Complete your assigned responsibilities for this team run";
    });

    console.log('[handleRunTeam] team members:', team.members.map(m => ({ id: m.id, task: m.task })));
    console.log('[handleRunTeam] memberTasks:', memberTasks);

    setRunningTeamIds(prev => new Set([...prev, team.id]));
    try {
      const result = await TeamAPI.startRun(team.id, team.goal, memberTasks);
      console.log('[handleRunTeam] run started:', result);
      // Auto-open Configure panel on Activity tab so user can watch
      const fullTeam = await TeamAPI.getTeam(team.id);
      setSelectedTeam(fullTeam);
      setOpenTabOnSelect('Activity');
    } catch (err: any) {
      console.error("Failed to start run:", err);
      alert(`Failed to start run: ${err.message}`);
    } finally {
      setTimeout(() => {
        setRunningTeamIds(prev => { const next = new Set(prev); next.delete(team.id); return next; });
      }, 5000);
    }
  };

  if (isLoading) {
    return <div className="p-8 text-center text-muted-foreground">Loading...</div>;
  }

  if (error) {
    return <div className="p-8 text-center text-destructive">{error}</div>;
  }

  return (
    <main className="min-h-screen w-full bg-background flex flex-col overflow-y-auto">
      <div className="border-b border-border bg-card sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Teams</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Manage and organize your teams
              </p>
            </div>
            <Button onClick={() => setIsModalOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Team
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 w-full mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {teams.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-muted">
              <Users className="h-10 w-10 text-muted-foreground" />
            </div>
            <h2 className="text-xl font-semibold text-foreground">No teams yet</h2>
            <p className="max-w-sm text-sm text-muted-foreground">
              Get started by creating your first team. Click the "Add Team" button to begin.
            </p>
            <Button
              onClick={() => setIsModalOpen(true)}
              className="mt-4 gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Your First Team
            </Button>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {teams.map((team) => (
              <TeamCard
                key={team.id}
                team={team}
                onConfigure={() => setSelectedTeam(team)}
                onChat={() => setActiveChatTeam(team)}
                onRun={() => handleRunTeam(team)}
                isRunning={runningTeamIds.has(team.id)}
              />
            ))}
          </div>
        )}
      </div>

      <CreateTeamModal
        open={isModalOpen}
        employees={employees}
        agentFiles={agentFiles}
        onOpenChange={setIsModalOpen}
        onCreateTeam={handleCreateTeam}
      />

      <TeamDetailsPanel
        team={selectedTeam}
        employees={employees}
        agentFiles={agentFiles}
        initialTab={openTabOnSelect}
        onClose={() => { setSelectedTeam(null); setOpenTabOnSelect(null); }}
        onUpdate={handleUpdateTeam}
        onDelete={handleDeleteTeam}
      />

      <TeamChatPanel
        team={activeChatTeam}
        onClose={() => setActiveChatTeam(null)}
      />
    </main>
  );
}
