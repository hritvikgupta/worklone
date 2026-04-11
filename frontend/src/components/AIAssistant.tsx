import React, { useState } from 'react';
import { Send, Sparkles, FileText, ListChecks, Loader2, X, Paperclip, Mic } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { sendChatMessage } from '@/lib/api';
import { ModelDropdown, AVAILABLE_MODELS } from '@/components/ModelDropdown';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'prd' | 'backlog';
}

interface AIAssistantProps {
  onClose?: () => void;
}

export function AIAssistant({ onClose }: AIAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "Hello! I'm Katy. I can help you write PRDs, prioritize your backlog, or brainstorm features. What's on your mind today?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState(AVAILABLE_MODELS[0].value);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Convert message history to API format
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await sendChatMessage({
        message: input,
        conversation_history: conversationHistory,
        model: selectedModel
      });

      if (response.success) {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: response.response,
          type: input.toLowerCase().includes('prd') || input.toLowerCase().includes('requirements') ? 'prd' : 'text'
        }]);
      } else {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: `Error: ${response.error || 'Unknown error occurred'}` 
        }]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: "Sorry, I encountered an error processing your request. Please make sure the backend server is running." 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#f7f7f5]">
      <div className="p-4 border-b border-zinc-200/50 flex items-center justify-between bg-[#f7f7f5] sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-zinc-900" />
          <h2 className="text-sm font-bold text-[#37352f]">Katy</h2>
        </div>
        {onClose && (
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8 text-zinc-400 hover:bg-zinc-200/50">
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        <ScrollArea className="flex-1 px-4">
          <div className="space-y-6 py-6">
            {messages.map((msg, i) => (
              <div key={i} className={cn(
                "flex gap-3",
                msg.role === 'user' ? "flex-row-reverse" : ""
              )}>
                <div className={cn(
                  "w-6 h-6 rounded flex items-center justify-center shrink-0 mt-0.5",
                  msg.role === 'assistant' ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-500"
                )}>
                  {msg.role === 'assistant' ? <Sparkles className="w-3 h-3" /> : <div className="text-[9px] font-bold">U</div>}
                </div>
                <div className={cn(
                  "max-w-[90%] text-xs leading-relaxed",
                  msg.role === 'assistant' ? "text-[#37352f]" : "bg-zinc-900 text-white px-3 py-2 rounded-xl shadow-sm"
                )}>
                  {msg.role === 'assistant' ? (
                    msg.type === 'prd' ? (
                      <div className="bg-white border border-zinc-200/50 rounded-lg p-4 space-y-3 shadow-sm">
                        <div className="flex items-center gap-2 pb-2 border-b border-zinc-100">
                          <FileText className="w-3 h-3 text-zinc-400" />
                          <span className="font-bold uppercase tracking-widest text-[9px] text-zinc-400">PRD Draft</span>
                        </div>
                        <div className="prose prose-xs max-w-none prose-zinc">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                    ) : (
                      <div className="prose prose-xs max-w-none prose-zinc">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    )
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded bg-zinc-900 text-white flex items-center justify-center shrink-0">
                  <Loader2 className="w-3 h-3 animate-spin" />
                </div>
                <div className="text-xs text-zinc-400 italic">
                  Thinking...
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="p-4 border-t border-zinc-200/50 bg-[#f7f7f5]">
          <div className="relative bg-white border border-zinc-200 rounded-xl p-3 shadow-sm focus-within:border-zinc-400 transition-colors">
            <textarea
              placeholder="Ask Katy anything..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="w-full bg-transparent border-none focus:ring-0 outline-none focus:outline-none shadow-none resize-none text-xs min-h-[44px] py-1 text-[#37352f] placeholder:text-zinc-400"
            />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-zinc-50">
              <div className="flex items-center gap-1">
                <ModelDropdown value={selectedModel} onChange={setSelectedModel} />
                <Button variant="ghost" size="icon" className="h-7 w-7 text-zinc-400 hover:text-zinc-900">
                  <Paperclip className="w-3 h-3" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-zinc-400 hover:text-zinc-900">
                  <Mic className="w-3 h-3" />
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button 
                  onClick={handleSend}
                  disabled={isLoading || !input.trim()}
                  size="icon"
                  className="bg-zinc-900 text-white hover:bg-zinc-800 h-7 w-7 rounded-lg transition-all active:scale-95"
                >
                  <Send className="w-3 h-3" />
                </Button>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {[
              { label: 'Draft PRD', icon: FileText, text: "Draft a PRD for a new dark mode feature" },
              { label: 'Prioritize', icon: ListChecks, text: "Prioritize my current backlog" },
            ].map((btn) => (
              <button 
                key={btn.label}
                onClick={() => setInput(btn.text)}
                className="flex items-center gap-1 px-2 py-0.5 rounded border border-zinc-200 bg-white text-[10px] font-medium text-zinc-500 hover:bg-zinc-50 hover:border-zinc-300 transition-all shadow-sm"
              >
                <btn.icon className="w-2.5 h-2.5" />
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
