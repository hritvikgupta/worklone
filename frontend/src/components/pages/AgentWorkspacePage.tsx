import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Settings2, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import {
  ChatSession,
  createEmployeeChatSession,
  getEmployeeChatSessionMessages,
  listEmployeeChatSessions,
  streamEmployeeChatEvents,
} from '@/lib/api';
import {
  listEmployees,
  getEmployee,
  updateEmployee,
  EmployeeDetail,
  EmployeeWithDetails,
} from '@/src/api/employees';
import { EmployeeConfigPanel } from '@/src/components/EmployeeConfigPanel';
import { EmployeeFormData } from '@/src/components/EmployeePanel';

type AgentMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
  status?: 'sending' | 'read';
};

function toConfigForm(employee: EmployeeWithDetails): EmployeeFormData {
  return {
    name: employee.employee.name,
    role: employee.employee.role,
    avatar_url: employee.employee.avatar_url,
    cover_url: employee.employee.cover_url || '',
    description: employee.employee.description,
    system_prompt: employee.employee.system_prompt,
    model: employee.employee.model,
    provider: employee.employee.provider || '',
    temperature: employee.employee.temperature,
    max_tokens: employee.employee.max_tokens,
    tools: employee.tools.filter((tool) => tool.is_enabled).map((tool) => tool.tool_name),
    skills: employee.skills.map((skill) => ({
      skill_name: skill.skill_name,
      category: skill.category,
      proficiency_level: skill.proficiency_level,
      description: skill.description,
    })),
    memory: employee.employee.memory || [],
  };
}

export function AgentWorkspacePage() {
  const [employees, setEmployees] = useState<EmployeeDetail[]>([]);
  const [loadingEmployees, setLoadingEmployees] = useState(true);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
  const [sessionsByEmployee, setSessionsByEmployee] = useState<Record<string, ChatSession[]>>({});
  const [activeSessionIdByEmployee, setActiveSessionIdByEmployee] = useState<Record<string, string>>({});
  const [messagesByEmployee, setMessagesByEmployee] = useState<Record<string, AgentMessage[]>>({});
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);
  const [configFormData, setConfigFormData] = useState<EmployeeFormData | null>(null);
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const selectedEmployee = useMemo(
    () => employees.find((employee) => employee.id === selectedEmployeeId) || null,
    [employees, selectedEmployeeId],
  );
  const activeMessages = messagesByEmployee[selectedEmployeeId] || [];

  useEffect(() => {
    let cancelled = false;
    async function loadEmployees() {
      setLoadingEmployees(true);
      try {
        const data = await listEmployees();
        if (cancelled) return;
        setEmployees(data);
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load employees:', error);
          setEmployees([]);
        }
      } finally {
        if (!cancelled) setLoadingEmployees(false);
      }
    }
    loadEmployees();
    return () => {
      cancelled = true;
    };
  }, []);

  const loadEmployeeSession = async (employeeId: string) => {
    try {
      const sessions = await listEmployeeChatSessions(employeeId);
      setSessionsByEmployee((prev) => ({ ...prev, [employeeId]: sessions }));
      if (sessions.length === 0) {
        setMessagesByEmployee((prev) => ({ ...prev, [employeeId]: [] }));
        return;
      }

      const latest = sessions[0];
      setActiveSessionIdByEmployee((prev) => ({ ...prev, [employeeId]: latest.id }));
      const history = await getEmployeeChatSessionMessages(employeeId, latest.id);
      setMessagesByEmployee((prev) => ({
        ...prev,
        [employeeId]: history.map((msg, index) => ({
          id: `${employeeId}-${latest.id}-${index}`,
          role: msg.role,
          content: msg.content,
          createdAt: new Date(msg.created_at),
          status: 'read',
        })),
      }));
    } catch (error) {
      console.error('Failed to load employee chat sessions:', error);
      setMessagesByEmployee((prev) => ({ ...prev, [employeeId]: [] }));
    }
  };

  const handleSelectEmployee = async (employeeId: string) => {
    setSelectedEmployeeId(employeeId);
    setInputValue('');
    if (sessionsByEmployee[employeeId] !== undefined) return;
    await loadEmployeeSession(employeeId);
  };

  const handleOpenConfig = async () => {
    if (!selectedEmployeeId) return;
    try {
      const detail = await getEmployee(selectedEmployeeId);
      setConfigFormData(toConfigForm(detail));
      setConfigOpen(true);
    } catch (error) {
      console.error('Failed to load employee config:', error);
    }
  };

  const handleSaveConfig = async (form: EmployeeFormData) => {
    if (!selectedEmployeeId) return;
    setIsSavingConfig(true);
    try {
      await updateEmployee(selectedEmployeeId, form);
      const refreshed = await listEmployees();
      setEmployees(refreshed);
      const detail = await getEmployee(selectedEmployeeId);
      setConfigFormData(toConfigForm(detail));
      setConfigOpen(false);
    } catch (error) {
      console.error('Failed to save employee config:', error);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSend = async () => {
    const text = inputValue.trim();
    if (!selectedEmployee || !text || isSending) return;

    const employeeId = selectedEmployee.id;
    const existingMessages = messagesByEmployee[employeeId] || [];

    let sessionId = activeSessionIdByEmployee[employeeId];
    if (!sessionId) {
      try {
        const session = await createEmployeeChatSession(employeeId, 'New Chat', selectedEmployee.model);
        sessionId = session.id;
        setActiveSessionIdByEmployee((prev) => ({ ...prev, [employeeId]: session.id }));
        setSessionsByEmployee((prev) => ({
          ...prev,
          [employeeId]: [session, ...(prev[employeeId] || [])],
        }));
      } catch (error) {
        console.error('Failed to create employee chat session:', error);
        return;
      }
    }

    const userMessage: AgentMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      createdAt: new Date(),
      status: 'read',
    };
    const assistantMessageId = `a-${Date.now()}`;
    const assistantMessage: AgentMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date(),
      status: 'sending',
    };

    setMessagesByEmployee((prev) => ({
      ...prev,
      [employeeId]: [...(prev[employeeId] || []), userMessage, assistantMessage],
    }));
    setInputValue('');
    setIsSending(true);

    try {
      const conversationHistory = existingMessages.map((message) => ({
        role: message.role,
        content: message.content,
      }));

      let buffer = '';
      const stream = streamEmployeeChatEvents(employeeId, {
        message: text,
        conversation_history: conversationHistory,
        model: selectedEmployee.model,
        session_id: sessionId,
      });

      for await (const event of stream) {
        if (event.type === 'content_token') {
          buffer += event.token || '';
          setMessagesByEmployee((prev) => ({
            ...prev,
            [employeeId]: (prev[employeeId] || []).map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: buffer } : msg
            ),
          }));
        } else if (event.type === 'final' && !buffer && event.content) {
          buffer = event.content;
          setMessagesByEmployee((prev) => ({
            ...prev,
            [employeeId]: (prev[employeeId] || []).map((msg) =>
              msg.id === assistantMessageId ? { ...msg, content: buffer } : msg
            ),
          }));
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Failed to stream response');
        }
      }

      setMessagesByEmployee((prev) => ({
        ...prev,
        [employeeId]: (prev[employeeId] || []).map((msg) =>
          msg.id === assistantMessageId ? { ...msg, status: 'read' } : msg
        ),
      }));
    } catch (error) {
      console.error('Failed to send employee message:', error);
      setMessagesByEmployee((prev) => ({
        ...prev,
        [employeeId]: (prev[employeeId] || []).map((msg) =>
          msg.id === assistantMessageId
            ? { ...msg, content: 'Failed to generate a response.', status: 'read' }
            : msg
        ),
      }));
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="h-full overflow-hidden bg-background">
      <div className="h-full px-8 pt-8 pb-44">
        <div className="mx-auto flex h-full max-w-6xl flex-col">
          <div className="mb-4 flex items-center justify-between border-b border-border pb-3">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Agent</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Select an employee, send prompts, and configure that employee model.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={handleOpenConfig}
              disabled={!selectedEmployeeId}
            >
              <Settings2 className="h-4 w-4" />
              Config
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto rounded-2xl border border-border bg-card/60 p-5">
            {loadingEmployees ? (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Loading employees...
              </div>
            ) : !selectedEmployeeId ? (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                Select an employee from the prompt bar below to start chatting.
              </div>
            ) : activeMessages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                No messages yet. Send the first prompt to {selectedEmployee?.name || 'this employee'}.
              </div>
            ) : (
              <div className="space-y-4">
                {activeMessages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      'flex',
                      message.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                        message.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-foreground'
                      )}
                    >
                      {message.content || (message.status === 'sending' ? 'Thinking...' : '')}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="fixed bottom-10 left-1/2 z-40 w-full max-w-3xl -translate-x-1/2 px-6">
        <div className="rounded-[24px] border border-border bg-card shadow-[0_8px_30px_rgb(0,0,0,0.08)] transition-all focus-within:border-foreground/15 focus-within:shadow-[0_8px_30px_rgb(0,0,0,0.12)]">
          <div className="px-4 pt-3 pb-2">
            <Select value={selectedEmployeeId} onValueChange={handleSelectEmployee}>
              <SelectTrigger className="h-9 w-[240px] border-border bg-background/80 text-sm">
                <SelectValue placeholder="Select employee" />
              </SelectTrigger>
              <SelectContent>
                {employees.map((employee) => (
                  <SelectItem key={employee.id} value={employee.id}>
                    {employee.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="px-4 pb-0">
            <Textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              placeholder={selectedEmployeeId ? 'Ask your employee...' : 'Select an employee to start'}
              className="min-h-[64px] max-h-[220px] w-full resize-none border-0 bg-transparent p-0 text-[15px] leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:ring-0 shadow-none"
              disabled={!selectedEmployeeId || isSending}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
            />
          </div>

          <div className="flex items-center justify-end p-4 pt-2">
            <Button
              size="icon"
              onClick={() => void handleSend()}
              disabled={!selectedEmployeeId || !inputValue.trim() || isSending}
              className={cn(
                'h-9 w-9 rounded-full transition-all duration-300',
                selectedEmployeeId && inputValue.trim() && !isSending
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground'
              )}
            >
              {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      <EmployeeConfigPanel
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        employee={configFormData}
        onSave={handleSaveConfig}
        isSaving={isSavingConfig}
      />
    </div>
  );
}
