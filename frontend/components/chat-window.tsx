"use client";

import { useState, useRef, useEffect } from 'react';
import { chat } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Card, CardContent } from '@/components/ui/card';
import { Send, Bot, User, ChevronDown, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    results?: any[];
}

function SourcesSection({ results }: { results: any[] }) {
    const [isOpen, setIsOpen] = useState(false);

    if (!results || results.length === 0) return null;

    return (
        <div className="space-y-2 mt-2">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
            >
                {isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                Sources ({results.length})
            </button>

            {isOpen && (
                <div className="grid gap-2 w-full animate-in fade-in slide-in-from-top-1 duration-200">
                    {results.map((result: any, idx: number) => (
                        <Card key={idx} className="bg-card border-muted">
                            <CardContent className="p-3 text-sm">
                                {result.type === 'image' ? (
                                    <div className="space-y-2">
                                        <div className="font-semibold text-xs text-muted-foreground">Image (Page {result.metadata.page})</div>
                                        <img
                                            src={`/api/${result.metadata.image_path}`}
                                            alt="Result"
                                            className="rounded-md max-h-48 object-contain bg-black/5"
                                        />
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        <div className="font-semibold text-xs text-muted-foreground">Text (Page {result.metadata.page})</div>
                                        <p className="line-clamp-3 text-muted-foreground">{result.content}</p>
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}

export interface ChatWindowProps {
    selectedTopic: string;
    onTopicChange: (topic: string) => void;
    topics: string[];
}

export function ChatWindow({ selectedTopic, onTopicChange, topics }: ChatWindowProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMessage: Message = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const data = await chat(userMessage.content, selectedTopic);
            const assistantMessage: Message = {
                role: 'assistant',
                content: data.answer,
                results: data.results
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong.' }]);
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-140px)] min-h-[500px] border rounded-lg bg-background">
            <ScrollArea className="flex-1 p-4">
                <div className="space-y-4">
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <Avatar>
                                <AvatarFallback>{msg.role === 'user' ? <User /> : <Bot />}</AvatarFallback>
                            </Avatar>
                            <div className={`flex flex-col gap-2 max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                <div className={`p-3 rounded-lg ${msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                                    {msg.role === 'assistant' && msg.results ? (
                                        <div className="space-y-4">
                                            <div className="prose dark:prose-invert text-sm max-w-none">
                                                <ReactMarkdown 
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        img: ({node, ...props}) => {
                                                            let src = props.src;
                                                            if (src && src.startsWith('/static')) {
                                                                src = `/api${src}`;
                                                            }
                                                            return (
                                                                <img 
                                                                    {...props} 
                                                                    src={src} 
                                                                    className="rounded-md max-h-80 w-auto object-contain bg-black/5 my-4 border border-border shadow-sm" 
                                                                />
                                                            );
                                                        }
                                                    }}
                                                >
                                                    {msg.content}
                                                </ReactMarkdown>
                                            </div>

                                            {msg.results.length > 0 && (
                                                <SourcesSection results={msg.results} />
                                            )}
                                        </div>
                                    ) : (
                                        msg.content
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex gap-3">
                            <Avatar>
                                <AvatarFallback><Bot /></AvatarFallback>
                            </Avatar>
                            <div className="bg-muted p-3 rounded-lg animate-pulse">Thinking...</div>
                        </div>
                    )}
                    <div ref={scrollRef} />
                </div>
            </ScrollArea>
            <div className="p-4 border-t flex flex-col gap-2">
                <select
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    value={selectedTopic}
                    onChange={(e) => onTopicChange(e.target.value)}
                >
                    {topics.map((t) => (
                        <option key={t} value={t}>
                            {t}
                        </option>
                    ))}
                </select>
                <div className="flex gap-2 items-end">
                    <Textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Ask about your documents..."
                        className="min-h-[40px] max-h-[200px]"
                    />
                    <Button onClick={handleSend} disabled={loading} className="h-10">
                        <Send className="w-4 h-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
