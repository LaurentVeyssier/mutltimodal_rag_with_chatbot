"use client";

import { useState, useEffect } from 'react';
import { ChatWindow } from '@/components/chat-window';
import { FileUpload } from '@/components/file-upload';
import { Button } from '@/components/ui/button';
import { getTopics } from '@/lib/api';

export default function Home() {
  const [selectedTopic, setSelectedTopic] = useState<string>("manrique");
  const [activeTab, setActiveTab] = useState<'chat' | 'upload'>('chat');
  const [topics, setTopics] = useState<string[]>([]);

  useEffect(() => {
    fetchTopics();
  }, []);

  const fetchTopics = async () => {
    try {
      const fetchedTopics = await getTopics();
      setTopics(fetchedTopics);
      // Ensure selected topic is in the list, if not default to first or multimodal_rag
      if (fetchedTopics.length > 0 && !fetchedTopics.includes(selectedTopic)) {
        // If current selected topic is not in list (e.g. initial load), keep it if it's the default, 
        // or switch to first available. For now, we trust the default.
        if (!fetchedTopics.includes("manrique")) {
          setTopics(prev => [...prev, "manrique"]);
        }
      }
    } catch (error) {
      console.error("Failed to fetch topics:", error);
    }
  };

  const handleTopicCreated = (newTopic: string) => {
    if (!topics.includes(newTopic)) {
      setTopics(prev => [...prev, newTopic]);
    }
    setSelectedTopic(newTopic);
  };

  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-accent selection:text-accent-foreground overflow-hidden flex flex-col md:flex-row">
      {/* Left Panel - The Visionary */}
      <div className="relative w-full md:w-5/12 lg:w-1/3 h-[20vh] min-h-[20vh] md:min-h-screen bg-primary/10 flex flex-col justify-end p-6 md:p-12 overflow-hidden">
        {/* Background Image */}
        <div
          className="absolute inset-0 z-0 opacity-100 bg-[url('/manrique_mobile.jpg')] md:bg-[url('/manrique.jpg')] bg-cover bg-center bg-no-repeat"
          style={{
            filter: 'grayscale(100%) contrast(1.1) brightness(0.9)' // Artistic B&W look
          }}
        />
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-background via-background/40 to-transparent md:bg-gradient-to-r md:from-transparent md:to-background/10 mix-blend-multiply" />
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/80 to-transparent md:hidden" />

        <div className="relative z-20 space-y-0 md:mb-20">
          <span className="uppercase tracking-widest text-[10px] md:text-sm font-bold text-accent">The Visionary</span>
          <h1 className="text-3xl md:text-7xl font-bold leading-none tracking-tighter text-white md:text-primary mix-blend-hard-light drop-shadow-lg md:drop-shadow-none">
            César <br />
            <span className="text-accent md:text-secondary">Manrique</span>
          </h1>
          <p className="text-white/90 md:text-muted-foreground text-sm md:text-xl font-light italic max-w-sm">
            Artist, architect, and activist.
          </p>
          <p className="text-white/90 md:text-muted-foreground text-sm md:text-xl font-light italic max-w-sm hidden md:block">
            "Art into nature, nature into art."
          </p>
          <p className="text-accent/90 md:text-secondary text-sm md:text-xl font-light italic max-w-sm">
            1919 - 1992
          </p>
        </div>
      </div>

      {/* Right Panel - Interaction */}
      <div className="flex-1 relative flex flex-col h-[80vh] md:h-screen">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-background to-background pointer-events-none" />

        <div className="relative z-10 flex-1 flex flex-col p-1 md:p-8 lg:p-12 gap-4 overflow-hidden">
          <header className="flex justify-between items-center pb-2 border-b border-border/40 shrink-0">
            <div>
              <h2 className="text-2xl font-display font-semibold text-foreground">
                {selectedTopic === 'manrique' ? 'Explore his Legacy' : 'Knowledge Base'}
              </h2>
            </div>

            <div className="flex bg-muted/40 p-1 rounded-lg border border-border/40 shrink-0">
              <Button
                variant={activeTab === 'chat' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('chat')}
                className="text-sm font-medium transition-all"
              >
                Chat
              </Button>
              <Button
                variant={activeTab === 'upload' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab('upload')}
                className="text-sm font-medium transition-all"
              >
                Upload
              </Button>
            </div>
          </header>

          <div className="flex-1 min-h-0 pb-2 flex flex-col">
            {activeTab === 'upload' && (
              <div className="space-y-6 overflow-y-auto pr-2 max-h-full animate-in fade-in zoom-in-95 duration-300">
                <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                  <FileUpload
                    selectedTopic={selectedTopic}
                    onTopicChange={setSelectedTopic}
                    topics={topics}
                    onTopicCreated={handleTopicCreated}
                  />
                </div>

                <div className="bg-secondary/5 rounded-2xl p-6 border border-secondary/10">
                  <h3 className="font-display text-lg text-secondary mb-2">Philosophy</h3>
                  <p className="text-sm text-muted-foreground">
                    Nature and art are not separate things. Manrique believed in organic architecture that respects the environment.
                  </p>
                </div>
              </div>
            )}

            {/* Chat Area */}
            {activeTab === 'chat' && (
              <div className="h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
                <div className="flex-1 bg-card/80 backdrop-blur-md rounded-2xl border border-white/20 shadow-xl overflow-hidden flex flex-col relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-white/40 to-white/10 pointer-events-none" />
                  <div className="relative z-10 flex-1 flex flex-col min-h-0 overflow-hidden">
                    <ChatWindow
                      selectedTopic={selectedTopic}
                      onTopicChange={setSelectedTopic}
                      topics={topics}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
