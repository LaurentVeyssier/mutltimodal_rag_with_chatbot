"use client";

import { useState, useEffect } from 'react';
import { ChatWindow } from '@/components/chat-window';
import { FileUpload } from '@/components/file-upload';
import { getTopics } from '@/lib/api';

export default function Home() {
  const [selectedTopic, setSelectedTopic] = useState<string>("manrique");
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
      <div className="relative w-full md:w-5/12 lg:w-1/3 min-h-[40vh] md:min-h-screen bg-primary/10 flex flex-col justify-end p-8 md:p-12 overflow-hidden">
        {/* Background Image */}
        <div
          className="absolute inset-0 z-0 opacity-100"
          style={{
            backgroundImage: "url('/manrique.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            filter: 'grayscale(100%) contrast(1.1) brightness(0.9)' // Artistic B&W look
          }}
        />
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-background via-background/40 to-transparent md:bg-gradient-to-r md:from-transparent md:to-background/10 mix-blend-multiply" />
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-black/80 to-transparent md:hidden" />

        <div className="relative z-20 space-y-4 md:mb-20">
          <span className="uppercase tracking-widest text-xs md:text-sm font-bold text-accent">The Visionary</span>
          <h1 className="text-5xl md:text-7xl font-bold leading-none tracking-tighter text-white md:text-primary mix-blend-hard-light drop-shadow-lg md:drop-shadow-none">
            César <br />
            <span className="text-accent md:text-secondary">Manrique</span>
          </h1>
          <p className="text-white/90 md:text-muted-foreground text-lg md:text-xl font-light italic max-w-sm">
            Artist, architect, and activist.
          </p>
          <p className="text-white/90 md:text-muted-foreground text-lg md:text-xl font-light italic max-w-sm">
            "Art into nature, nature into art."
          </p>
        </div>
      </div>

      {/* Right Panel - Interaction */}
      <div className="flex-1 relative flex flex-col h-[60vh] md:h-screen">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-background to-background pointer-events-none" />

        <div className="relative z-10 flex-1 flex flex-col p-4 md:p-8 lg:p-12 gap-8 overflow-hidden">
          <header className="flex justify-between items-center pb-6 border-b border-border/40 shrink-0">
            <div>
              <h2 className="text-2xl font-display font-semibold text-foreground">
                {selectedTopic === 'manrique' ? 'Explore his Legacy' : 'Knowledge Base'}
              </h2>
              <p className="text-sm text-muted-foreground">Ask questions, upload documents, and discover.</p>
            </div>
            {/* Topic Selector could be moved here or kept in fileupload/chat */}
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0 pb-2">
            {/* Sidebar / Upload Area - Mobile: Collapsible or Top, Desktop: Left Col */}
            <div className="lg:col-span-4 space-y-6 overflow-y-auto lg:overflow-visible pr-2 lg:pr-0">
              <div className="bg-card/50 backdrop-blur-sm border border-border/50 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                <FileUpload
                  selectedTopic={selectedTopic}
                  onTopicChange={setSelectedTopic}
                  topics={topics}
                  onTopicCreated={handleTopicCreated}
                />
              </div>

              <div className="bg-secondary/5 rounded-2xl p-6 border border-secondary/10 hidden lg:block">
                <h3 className="font-display text-lg text-secondary mb-2">Philosophy</h3>
                <p className="text-sm text-muted-foreground">
                  Nature and art are not separate things. Manrique believed in organic architecture that respects the environment.
                </p>
              </div>
            </div>

            {/* Chat Area */}
            <div className="lg:col-span-8 h-full min-h-0 flex flex-col">
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
          </div>
        </div>
      </div>
    </main>
  );
}
