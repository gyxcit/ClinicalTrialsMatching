"""
Memory
-----------
A simple memory module to store and retrieve conversation history for an AI agent.
"""
from typing import List, Dict, Optional


class Memory:
    """Simple memory store for conversation history with size management.
    
    Attributes:
        max_history: Maximum number of messages to keep (None for unlimited)
        history: List of message dictionaries with 'role' and 'content'
    """

    def __init__(self, max_history: Optional[int] = None):
        """Initialize memory with optional size limit.
        
        Args:
            max_history: Maximum number of messages to keep. If None, unlimited.
        """
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history

    def add(self, role: str, content: str) -> None:
        """Add a message to history.
        
        Args:
            role: The role of the message sender (user, assistant, system, tool)
            content: The content of the message
        """
        self.history.append({"role": role, "content": content})
        
        # Trim history if it exceeds max_history
        if self.max_history and len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get(self, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history.
        
        Args:
            last_n: If specified, return only the last n messages
            
        Returns:
            List of message dictionaries
        """
        if last_n:
            return self.history[-last_n:].copy()
        return self.history.copy()
    
    def clear(self) -> None:
        """Clear all conversation history."""
        self.history = []
    
    def size(self) -> int:
        """Get the number of messages in history.
        
        Returns:
            Number of messages
        """
        return len(self.history)