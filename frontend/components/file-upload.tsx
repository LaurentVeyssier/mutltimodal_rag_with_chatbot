"use client";

import { useState } from 'react';
import { uploadFile } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';

export interface FileUploadProps {
    selectedTopic: string;
    onTopicChange: (topic: string) => void;
    topics: string[];
    onTopicCreated: (topic: string) => void;
}

export function FileUpload({ selectedTopic, onTopicChange, topics, onTopicCreated }: FileUploadProps) {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [message, setMessage] = useState('');
    const [isCreating, setIsCreating] = useState(false);
    const [newTopicName, setNewTopicName] = useState('');

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setStatus('idle');
            setMessage('');
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        try {
            await uploadFile(file, selectedTopic);
            setStatus('success');
            setMessage('File uploaded successfully!');
            setFile(null);
        } catch (error) {
            setStatus('error');
            setMessage('Failed to upload file.');
            console.error(error);
        } finally {
            setUploading(false);
        }
    };

    const handleTopicSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const value = e.target.value;
        if (value === 'CREATE_NEW_TOPIC_OPTION') {
            setIsCreating(true);
            setNewTopicName('');
        } else {
            onTopicChange(value);
        }
    };

    const handleCreateTopic = () => {
        if (newTopicName.trim()) {
            onTopicCreated(newTopicName.trim());
            setIsCreating(false);
        }
    };

    const handleCancelCreate = () => {
        setIsCreating(false);
        setNewTopicName('');
    };

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <Upload className="w-5 h-5" />
                    Upload Document
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">Topic Name</label>
                    {!isCreating ? (
                        <select
                            className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            value={selectedTopic}
                            onChange={handleTopicSelect}
                        >
                            {topics.map((t) => (
                                <option key={t} value={t}>
                                    {t}
                                </option>
                            ))}
                            <option value="CREATE_NEW_TOPIC_OPTION">Create new topic...</option>
                        </select>
                    ) : (
                        <div className="flex gap-2">
                            <Input
                                type="text"
                                value={newTopicName}
                                onChange={(e) => setNewTopicName(e.target.value)}
                                placeholder="Enter new topic name"
                                autoFocus
                            />
                            <Button size="sm" onClick={handleCreateTopic} disabled={!newTopicName.trim()}>
                                Add
                            </Button>
                            <Button size="sm" variant="outline" onClick={handleCancelCreate}>
                                Cancel
                            </Button>
                        </div>
                    )}
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium">Document</label>
                    <Input type="file" accept=".pdf" onChange={handleFileChange} />
                </div>
                <Button
                    onClick={handleUpload}
                    disabled={!file || uploading}
                    className="w-full"
                >
                    {uploading ? 'Uploading...' : 'Upload PDF'}
                </Button>
                {status === 'success' && (
                    <div className="flex items-center gap-2 text-green-600 text-sm">
                        <CheckCircle className="w-4 h-4" />
                        {message}
                    </div>
                )}
                {status === 'error' && (
                    <div className="flex items-center gap-2 text-red-600 text-sm">
                        <AlertCircle className="w-4 h-4" />
                        {message}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
