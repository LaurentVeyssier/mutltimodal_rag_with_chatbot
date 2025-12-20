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

export const chat = async (query: string, topic: string, history: any[] = []) => {
  const response = await axios.post(`${API_URL}/chat`, { query, topic, history });
  return response.data;
};

export const getTopics = async () => {
  const response = await axios.get(`${API_URL}/topics`);
  return response.data.topics;
};
