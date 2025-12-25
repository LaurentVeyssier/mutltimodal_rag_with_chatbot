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

const SUGGESTED_QUESTIONS = [
    "Tell me who is César Manrique?",
    "Where and when were you born?",
    "How would you describe yourself as an artist and as a person?",
    "What inspired you?",
    "Where did you live?",
    "What artistic disciplines did you work in (painting, sculpture, architecture, design)?",
    "Why are you considered an important cultural figure, not only an artist?",
    "What role did you play for Lanzarote?",
    "How did Lanzarote influence your art and way of thinking?",
    "You lived in New York. How did it influence your artistic vision?",
    "How do art, architecture, and landscape coexist in your work?",
    "What role do nature and vegetation play in your creations?",
    "What do you consider to be your legacy today?",
    "Tell me about the César Manrique Foundation",
    "Tell me about your most important artworks",
    "What is your artistic philosophy?",
    "What do you mean by mimesis, and why is it important in your work?",
    "Who did you collaborate with?",
    "Who inspired you?",
    "Detail your work and philosophy for educated art experts",
    "How did your belief in the unity of art and nature crystallize through your work?",
    "What criteria guided your decision-making when transforming natural sites into artistic spaces?",
    "How do your major works articulate an ethics over nature?",
    "How do works such as Jameos del Agua or Mirador del Río embody your concept of “total art”?",
    "How should your works be read today—as aesthetic achievements, ecological statements, or cultural manifestos?",
    "How did you reconcile a deeply local identity with the pursuit of a universal artistic language?",
];


interface Message {
    role: 'user' | 'assistant';
    content: string;
    results?: any[];
    follow_up?: string;
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
                                        <div className="font-semibold text-xs text-muted-foreground">
                                            Image (Page {result.metadata.page}) • {result.metadata.source?.split(/[\\/]/).pop()}
                                        </div>
                                        <img
                                            src={(() => {
                                                const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
                                                const path = result.metadata.image_path;
                                                return path?.startsWith('http') ? path : `${apiUrl}/${path}`;
                                            })()}
                                            alt="Result"
                                            className="rounded-md max-h-48 object-contain bg-black/5"
                                        />
                                    </div>
                                ) : (
                                    <div className="space-y-1">
                                        <div className="font-semibold text-xs text-muted-foreground">
                                            Text (Page {result.metadata.page}) • {result.metadata.source?.split(/[\\/]/).pop()}
                                        </div>
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
    const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Randomly select 3 questions on mount
        const shuffled = [...SUGGESTED_QUESTIONS].sort(() => 0.5 - Math.random());
        setSuggestedQuestions(shuffled.slice(0, 3));
    }, []);


    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    const handleSend = async (text?: string) => {
        const content = text || input;
        if (!content.trim()) return;

        const userMessage: Message = { role: 'user', content: content };
        setMessages(prev => [...prev, userMessage]);
        if (!text) setInput(''); // Only clear input if typed

        setLoading(true);

        try {
            // Prepare history (all messages except the one we just added locally)
            // We need to map them to the format expected by backend if necessary, 
            // but the current Message interface {role, content} matches what we want.
            const history = messages.map(m => ({ role: m.role, content: m.content }));

            const data = await chat(userMessage.content, selectedTopic, history);
            const assistantMessage: Message = {
                role: 'assistant',
                content: data.answer,
                results: data.results,
                follow_up: data.follow_up
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
        <div className="flex flex-col h-full min-h-0 border-0 bg-transparent overflow-hidden relative">
            <ScrollArea className="flex-1 h-full w-full p-4 min-h-0">
                <div className="space-y-4 pb-4">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full space-y-4 mt-8 opacity-70">
                            <Bot className="w-12 h-12 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground font-medium">Ask César anything...</p>
                            <div className="flex flex-wrap justify-center gap-2 w-full max-w-lg">
                                {suggestedQuestions.map((q, i) => (
                                    <Button
                                        key={i}
                                        variant="outline"
                                        className="text-xs h-auto py-2 whitespace-normal text-left shrink"
                                        onClick={() => handleSend(q)}
                                        disabled={loading}
                                    >
                                        {q}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    )}
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
                                                        img: ({ node, ...props }) => {
                                                            let src = props.src;
                                                            const apiUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
                                                            if (typeof src === 'string' && src.startsWith('/static')) {
                                                                src = `${apiUrl}${src}`;
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
                                                    {msg.content.replace(/<follow_up>[\s\S]*?<\/follow_up>/g, '').trim()}
                                                </ReactMarkdown>
                                            </div>

                                            {msg.results.length > 0 && (
                                                <SourcesSection results={msg.results} />
                                            )}

                                            {msg.follow_up && i === messages.length - 1 && (
                                                <div className="mt-4 pt-4 border-t border-border/50">
                                                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Suggested Follow-up (click to continue)</p>
                                                    <Button
                                                        variant="outline"
                                                        className="text-xs h-auto py-2 px-3 whitespace-normal text-left justify-start w-full hover:bg-primary/5 hover:text-primary transition-all border-dashed shrink"
                                                        onClick={() => handleSend(msg.follow_up)}
                                                        disabled={loading}
                                                    >
                                                        {msg.follow_up}
                                                    </Button>
                                                </div>
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
                    className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-base md:text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
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
                    <Button onClick={() => handleSend()} disabled={loading} className="h-10">
                        <Send className="w-4 h-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
