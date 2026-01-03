"""Agent memory and context management system"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from enum import Enum


class MemoryType(Enum):
    """Types of memory entries"""
    USER_INPUT = "user_input"
    AGENT_RESPONSE = "agent_response"
    SYSTEM_EVENT = "system_event"
    ERROR = "error"
    FEEDBACK = "feedback"


@dataclass
class MemoryEntry:
    """Single memory entry"""
    timestamp: str
    memory_type: MemoryType
    content: str
    metadata: Dict[str, Any]
    agent_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            **asdict(self),
            'memory_type': self.memory_type.value
        }


class AgentMemory:
    """Manages agent memory and context"""
    
    def __init__(self, max_entries: int = 100):
        """
        Initialize memory system
        
        Args:
            max_entries: Maximum number of entries to keep
        """
        self.max_entries = max_entries
        self.memories: List[MemoryEntry] = []
        self.context: Dict[str, Any] = {}
        
    def add_memory(
        self,
        memory_type: MemoryType,
        content: str,
        agent_name: Optional[str] = None,
        **metadata
    ) -> None:
        """
        Add a memory entry
        
        Args:
            memory_type: Type of memory
            content: Memory content
            agent_name: Associated agent name
            **metadata: Additional metadata
        """
        entry = MemoryEntry(
            timestamp=datetime.now().isoformat(),
            memory_type=memory_type,
            content=content,
            metadata=metadata,
            agent_name=agent_name
        )
        
        self.memories.append(entry)
        
        # Trim if exceeds max
        if len(self.memories) > self.max_entries:
            self.memories = self.memories[-self.max_entries:]
    
    def get_recent_memories(
        self,
        count: int = 10,
        memory_type: Optional[MemoryType] = None,
        agent_name: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Get recent memories
        
        Args:
            count: Number of memories to retrieve
            memory_type: Filter by memory type
            agent_name: Filter by agent name
            
        Returns:
            List of memory entries
        """
        filtered = self.memories
        
        if memory_type:
            filtered = [m for m in filtered if m.memory_type == memory_type]
        
        if agent_name:
            filtered = [m for m in filtered if m.agent_name == agent_name]
        
        return filtered[-count:]
    
    def update_context(self, key: str, value: Any) -> None:
        """Update context variable"""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context variable"""
        return self.context.get(key, default)
    
    def get_conversation_history(
        self,
        agent_name: Optional[str] = None,
        max_entries: int = 20
    ) -> List[Dict[str, str]]:
        """
        Get conversation history in chat format
        
        Args:
            agent_name: Filter by agent name
            max_entries: Maximum entries to return
            
        Returns:
            List of messages in format [{"role": "user/assistant", "content": "..."}]
        """
        history = []
        
        for memory in self.get_recent_memories(count=max_entries * 2, agent_name=agent_name):
            if memory.memory_type == MemoryType.USER_INPUT:
                history.append({"role": "user", "content": memory.content})
            elif memory.memory_type == MemoryType.AGENT_RESPONSE:
                history.append({"role": "assistant", "content": memory.content})
        
        return history[-max_entries:]
    
    def clear_agent_memory(self, agent_name: str) -> None:
        """Clear memories for specific agent"""
        self.memories = [m for m in self.memories if m.agent_name != agent_name]
    
    def export_memories(self) -> str:
        """Export memories as JSON"""
        return json.dumps([m.to_dict() for m in self.memories], indent=2)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get memory summary"""
        return {
            'total_memories': len(self.memories),
            'by_type': {
                mem_type.value: len([m for m in self.memories if m.memory_type == mem_type])
                for mem_type in MemoryType
            },
            'by_agent': {
                agent: len([m for m in self.memories if m.agent_name == agent])
                for agent in set(m.agent_name for m in self.memories if m.agent_name)
            },
            'context_keys': list(self.context.keys())
        }
