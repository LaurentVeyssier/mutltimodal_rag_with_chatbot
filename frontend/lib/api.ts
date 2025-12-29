import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

export const uploadFile = async (file: File, topic: string) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('topic', topic);
  const response = await axios.post(`${API_URL}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const chat = async (query: string, topic: string, history: any[] = [], onStatus?: (status: string) => void) => {
  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query, topic, history }),
  });

  if (!response.ok) {
    throw response;
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('Failed to read response stream');

  const decoder = new TextDecoder();
  let result: any = null;
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || ''; // Keep the last incomplete line in buffer

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const data = JSON.parse(line);
        if (data.type === 'status') {
          onStatus?.(data.message);
        } else if (data.type === 'data') {
          result = data;
        } else if (data.type === 'error') {
          throw new Error(data.message);
        }
      } catch (e) {
        console.error('Error parsing stream chunk:', e, line);
      }
    }
  }

  return result;
};

export const getTopics = async () => {
  const response = await axios.get(`${API_URL}/topics`);
  return response.data.topics;
};
