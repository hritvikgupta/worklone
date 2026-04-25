import React, { useState } from 'react';
import { Send, Swords } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function AgentArenaPage() {
  const [prompt, setPrompt] = useState('');
  const [messagesA, setMessagesA] = useState<{ role: string; content: string }[]>([]);
  const [messagesB, setMessagesB] = useState<{ role: string; content: string }[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [voted, setVoted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    setMessagesA(prev => [...prev, { role: 'user', content: prompt }]);
    setMessagesB(prev => [...prev, { role: 'user', content: prompt }]);
    setIsGenerating(true);
    setVoted(false);
    
    // Simulate generation
    setTimeout(() => {
      setMessagesA(prev => [...prev, { role: 'assistant', content: 'This is a simulated response from Model A. It provides a detailed answer to your prompt using its distinct style.' }]);
      setMessagesB(prev => [...prev, { role: 'assistant', content: 'Here is Model B\'s response. It might be shorter or longer, but it represents a different approach to the same prompt.' }]);
      setIsGenerating(false);
      setPrompt('');
    }, 1500);
  };

  return (
    <div className="flex flex-col h-full bg-background text-foreground">
      <div className="flex items-center gap-3 p-6 border-b border-border bg-card/50 shrink-0">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
          <Swords className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Agent Arena</h1>
          <p className="text-sm text-muted-foreground">Battle test different AI models side-by-side</p>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col max-w-6xl mx-auto w-full p-6">
        <div className="grid grid-cols-2 gap-6 flex-1 min-h-0">
          {/* Model A */}
          <div className="flex flex-col border border-border rounded-xl bg-card overflow-hidden">
            <div className="p-3 border-b border-border bg-muted/30 font-medium text-sm text-center shrink-0">
              Model A
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messagesA.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                    msg.role === 'user' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-foreground'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isGenerating && (
                <div className="flex justify-start">
                  <div className="bg-muted text-foreground max-w-[85%] rounded-2xl px-4 py-2 flex items-center gap-2">
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-75" />
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-150" />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Model B */}
          <div className="flex flex-col border border-border rounded-xl bg-card overflow-hidden">
            <div className="p-3 border-b border-border bg-muted/30 font-medium text-sm text-center shrink-0">
              Model B
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messagesB.map((msg, i) => (
                <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                    msg.role === 'user' 
                      ? 'bg-primary text-primary-foreground' 
                      : 'bg-muted text-foreground'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isGenerating && (
                <div className="flex justify-start">
                  <div className="bg-muted text-foreground max-w-[85%] rounded-2xl px-4 py-2 flex items-center gap-2">
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce" />
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-75" />
                    <div className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce delay-150" />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Voting area */}
        {messagesA.length > 0 && !isGenerating && !voted && (
          <div className="flex justify-center gap-3 mt-6 shrink-0">
            <Button variant="outline" onClick={() => setVoted(true)}>👈 Model A is better</Button>
            <Button variant="outline" onClick={() => setVoted(true)}>Tie</Button>
            <Button variant="outline" onClick={() => setVoted(true)}>Both are bad</Button>
            <Button variant="outline" onClick={() => setVoted(true)}>Model B is better 👉</Button>
          </div>
        )}
        
        {voted && (
          <div className="text-center mt-6 p-4 bg-muted/50 rounded-lg text-sm font-medium text-muted-foreground shrink-0">
            Thanks for voting! Models revealed: <span className="text-foreground font-bold">GPT-4o</span> vs <span className="text-foreground font-bold">Claude 3.5 Sonnet</span>
          </div>
        )}

        {/* Input area */}
        <div className="mt-6 shrink-0">
          <form onSubmit={handleSubmit} className="relative">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Send a prompt to both models..."
              className="w-full pl-4 pr-12 py-4 bg-card border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent shadow-sm"
              disabled={isGenerating}
            />
            <Button 
              type="submit" 
              size="icon" 
              className="absolute right-2 top-2 bottom-2 h-auto"
              disabled={!prompt.trim() || isGenerating}
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
