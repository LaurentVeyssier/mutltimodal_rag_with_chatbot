import sys
from pathlib import Path
import os

# Add parent directory to sys.path to import rag_engine
sys.path.append(str(Path(__file__).resolve().parent))

from rag_engine import RAGEngine
import unittest
from unittest.mock import MagicMock, patch

class TestFollowUp(unittest.TestCase):
    def setUp(self):
        # Mock Pinecone and GenAI to avoid actual API calls
        with patch('rag_engine.Pinecone'), \
             patch('rag_engine.genai.Client'), \
             patch('rag_engine.storage.Client'), \
             patch('rag_engine.detector'):
            self.rag = RAGEngine()
            self.rag.index = MagicMock()
            self.rag.llm = MagicMock()

    def test_extract_follow_up(self):
        # Mock LLM response with tags
        mock_response = MagicMock()
        mock_response.text = "This is the answer. <follow_up>What about the foundation?</follow_up>"
        self.rag.llm.models.generate_content.return_value = mock_response
        
        # Test generate_answer
        result = self.rag.generate_answer("test query", [])
        self.assertEqual(result["follow_up"], "What about the foundation?")
        # The answer should STILL have the tags because we want them in history
        self.assertIn("<follow_up>", result["answer"])
        self.assertIn("This is the answer.", result["answer"])

    def test_yes_substitution(self):
        # Mock history with a follow-up tag
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "Hello! <follow_up>Tell me more about your art?</follow_up>"}
        ]
        
        # Mock retrieve and generate_answer
        self.rag.retrieve = MagicMock(return_value=[])
        self.rag.generate_answer = MagicMock(return_value={"answer": "ok", "follow_up": None})
        
        # Call search with "yes"
        self.rag.search("yes", history=history)
        
        # Verify that retrieve was called with the suggested question
        self.rag.retrieve.assert_called_with("Tell me more about your art?", "manrique", 5)

if __name__ == '__main__':
    unittest.main()
