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
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900">
            {selectedTopic === 'manrique' ? 'César Manrique: Voice of Lanzarote' : 'Multimodal RAG'}
          </h1>
          <p className="text-slate-500">Upload PDFs and search through text and images.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-1">
            <FileUpload
              selectedTopic={selectedTopic}
              onTopicChange={setSelectedTopic}
              topics={topics}
              onTopicCreated={handleTopicCreated}
            />
          </div>
          <div className="md:col-span-2">
            <ChatWindow
              selectedTopic={selectedTopic}
              onTopicChange={setSelectedTopic}
              topics={topics}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
