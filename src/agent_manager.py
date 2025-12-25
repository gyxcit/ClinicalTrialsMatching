"""
Agent Manager for Mistral AI agents.
Provides a clean interface to create, manage and interact with agents.
Supports both synchronous and asynchronous operations.
"""
from typing import Optional, List, Dict, Any, Type, TypeVar
from dataclasses import dataclass
from enum import Enum
import time
import asyncio
import json
from mistralai import Mistral
from pydantic import BaseModel, ValidationError

from .config import AGENT_API_KEY
from .logger import (
    logger,
    log_agent_action,
    log_llm_interaction,
    log_success,
    log_error,
    log_warning
)


class AgentModel(Enum):
    """Available Mistral models."""
    SMALL = "mistral-small-latest"
    MEDIUM = "mistral-medium-latest"
    LARGE = "mistral-large-latest"
    CODESTRAL = "codestral-latest"


class ResponseFormat(Enum):
    """Available response formats."""
    TEXT = "text"
    JSON = "json_object"
    STRUCTURED = "structured"  # With Pydantic validation


T = TypeVar('T', bound=BaseModel)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_id: str
    name: str
    model: str = AgentModel.SMALL.value
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    description: str = ""
    response_format: Optional[ResponseFormat] = None
    response_model: Optional[Type[BaseModel]] = None


class MistralAgent:
    """Represents a Mistral AI agent with its configuration and methods."""
    
    def __init__(self, config: AgentConfig, client: Mistral):
        """
        Initialize an agent.
        
        Args:
            config: Agent configuration
            client: Mistral client instance
        """
        self.config = config
        self.client = client
        self.conversation_history: List[Dict[str, str]] = []
        
        log_success(f"Agent '{config.name}' initialized (ID: {config.agent_id})")
    
    def _parse_response(self, response: Any, response_model: Optional[Type[T]] = None) -> Any:
        """
        Parse and validate response based on format.
        
        Args:
            response: Raw response from agent
            response_model: Optional Pydantic model for validation
            
        Returns:
            Parsed response
        """
        # If no specific format, return as is
        if not self.config.response_format and not response_model:
            return response
        
        # Extract content from response
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
        else:
            content = str(response)
        
        # Parse based on format
        if response_model or self.config.response_model:
            model_to_use = response_model or self.config.response_model
            try:
                # Try to parse as JSON first
                if isinstance(content, str):
                    data = json.loads(content)
                else:
                    data = content
                
                validated = model_to_use(**data)
                log_success(f"Response validated with {model_to_use.__name__}")
                return validated
                
            except (json.JSONDecodeError, ValidationError) as e:
                log_warning(f"Failed to validate response: {e}")
                return content
        
        elif self.config.response_format == ResponseFormat.JSON:
            try:
                return json.loads(content) if isinstance(content, str) else content
            except json.JSONDecodeError as e:
                log_warning(f"Failed to parse JSON response: {e}")
                return content
        
        return content
    
    def chat(
        self, 
        message: str, 
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message to the agent (synchronous).
        
        Args:
            message: User message
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response (parsed according to response_model if provided)
        """
        try:
            log_agent_action(f"Sending message to '{self.config.name}'", f"Length: {len(message)} chars")
            log_llm_interaction(self.config.model, len(message))
            
            # Add message to history
            self.conversation_history.append({
                "role": "user",
                "content": message
            })
            
            # Prepare request parameters
            request_params = {
                "messages": [{"role": "user", "content": message}],
                "agent_id": self.config.agent_id,
                "stream": stream
            }
            
            # Add response format if specified
            if response_model or self.config.response_model:
                request_params["response_format"] = {"type": "json_object"}
            elif self.config.response_format == ResponseFormat.JSON:
                request_params["response_format"] = {"type": "json_object"}
            
            # Call agent
            response = self.client.agents.complete(**request_params)
            
            # Parse response
            parsed_response = self._parse_response(response, response_model)
            
            # Log response
            response_str = str(parsed_response)
            log_llm_interaction(self.config.model, len(message), len(response_str))
            log_success(f"Response received from '{self.config.name}'")
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant", 
                "content": response_str
            })
            
            return parsed_response
            
        except Exception as e:
            log_error(f"Failed to get response from agent '{self.config.name}'", e)
            raise
    
    async def chat_async(
        self, 
        message: str, 
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message to the agent (asynchronous).
        
        Args:
            message: User message
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response (parsed according to response_model if provided)
        """
        try:
            log_agent_action(f"[ASYNC] Sending message to '{self.config.name}'", f"Length: {len(message)} chars")
            log_llm_interaction(self.config.model, len(message))
            
            # Add message to history
            self.conversation_history.append({
                "role": "user",
                "content": message
            })
            
            # Prepare request parameters
            request_params = {
                "messages": [{"role": "user", "content": message}],
                "agent_id": self.config.agent_id,
                "stream": stream
            }
            
            # Add response format if specified
            if response_model or self.config.response_model:
                request_params["response_format"] = {"type": "json_object"}
            elif self.config.response_format == ResponseFormat.JSON:
                request_params["response_format"] = {"type": "json_object"}
            
            # Call agent asynchronously
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.agents.complete(**request_params)
            )
            
            # Parse response
            parsed_response = self._parse_response(response, response_model)
            
            # Log response
            response_str = str(parsed_response)
            log_llm_interaction(self.config.model, len(message), len(response_str))
            log_success(f"[ASYNC] Response received from '{self.config.name}'")
            
            # Add response to history
            self.conversation_history.append({
                "role": "assistant", 
                "content": response_str
            })
            
            return parsed_response
            
        except Exception as e:
            log_error(f"[ASYNC] Failed to get response from agent '{self.config.name}'", e)
            raise
    
    def chat_with_history(
        self, 
        message: str, 
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message with conversation history context (synchronous).
        
        Args:
            message: User message
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response (parsed according to response_model if provided)
        """
        try:
            log_agent_action(
                f"Chat with history for '{self.config.name}'", 
                f"History: {len(self.conversation_history)} messages"
            )
            
            # Add new message
            messages = self.conversation_history + [{
                "role": "user",
                "content": message
            }]
            
            log_llm_interaction(self.config.model, len(message))
            
            # Prepare request parameters
            request_params = {
                "messages": messages,
                "agent_id": self.config.agent_id,
                "stream": stream
            }
            
            # Add response format if specified
            if response_model or self.config.response_model:
                request_params["response_format"] = {"type": "json_object"}
            elif self.config.response_format == ResponseFormat.JSON:
                request_params["response_format"] = {"type": "json_object"}
            
            response = self.client.agents.complete(**request_params)
            
            # Parse response
            parsed_response = self._parse_response(response, response_model)
            
            response_str = str(parsed_response)
            log_llm_interaction(self.config.model, len(message), len(response_str))
            log_success(f"Response with history received from '{self.config.name}'")
            
            # Update history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response_str})
            
            return parsed_response
            
        except Exception as e:
            log_error(f"Failed to chat with history for '{self.config.name}'", e)
            raise
    
    async def chat_with_history_async(
        self, 
        message: str, 
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message with conversation history context (asynchronous).
        
        Args:
            message: User message
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response (parsed according to response_model if provided)
        """
        try:
            log_agent_action(
                f"[ASYNC] Chat with history for '{self.config.name}'", 
                f"History: {len(self.conversation_history)} messages"
            )
            
            # Add new message
            messages = self.conversation_history + [{
                "role": "user",
                "content": message
            }]
            
            log_llm_interaction(self.config.model, len(message))
            
            # Prepare request parameters
            request_params = {
                "messages": messages,
                "agent_id": self.config.agent_id,
                "stream": stream
            }
            
            # Add response format if specified
            if response_model or self.config.response_model:
                request_params["response_format"] = {"type": "json_object"}
            elif self.config.response_format == ResponseFormat.JSON:
                request_params["response_format"] = {"type": "json_object"}
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.agents.complete(**request_params)
            )
            
            # Parse response
            parsed_response = self._parse_response(response, response_model)
            
            response_str = str(parsed_response)
            log_llm_interaction(self.config.model, len(message), len(response_str))
            log_success(f"[ASYNC] Response with history received from '{self.config.name}'")
            
            # Update history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response_str})
            
            return parsed_response
            
        except Exception as e:
            log_error(f"[ASYNC] Failed to chat with history for '{self.config.name}'", e)
            raise
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        log_agent_action(f"Cleared history for '{self.config.name}'")
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.config.name,
            "agent_id": self.config.agent_id,
            "model": self.config.model,
            "description": self.config.description,
            "temperature": self.config.temperature,
            "response_format": self.config.response_format.value if self.config.response_format else None,
            "response_model": self.config.response_model.__name__ if self.config.response_model else None,
            "history_length": len(self.conversation_history)
        }


class AgentManager:
    """Manager for creating and managing Mistral AI agents."""
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the agent manager.
        
        Args:
            api_key: Mistral API key (uses AGENT_API_KEY from config if not provided)
            max_retries: Maximum number of retries for failed requests
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key or AGENT_API_KEY
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.agents: Dict[str, MistralAgent] = {}
        self._client: Optional[Mistral] = None
        
        log_success("AgentManager initialized")
    
    @property
    def client(self) -> Mistral:
        """Get or create Mistral client."""
        if self._client is None:
            self._client = Mistral(api_key=self.api_key)
            log_agent_action("Mistral client created")
        return self._client
    
    def create_agent(
        self,
        agent_id: str,
        name: str,
        model: str = AgentModel.SMALL.value,
        temperature: float = 0.7,
        description: str = "",
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[ResponseFormat] = None,
        response_model: Optional[Type[BaseModel]] = None
    ) -> MistralAgent:
        """
        Create a new agent.
        
        Args:
            agent_id: Unique agent ID from Mistral
            name: Human-readable name for the agent
            model: Model to use
            temperature: Temperature for generation
            description: Agent description
            tools: Optional tools configuration
            max_tokens: Maximum tokens for response
            response_format: Format for responses (TEXT, JSON, STRUCTURED)
            response_model: Pydantic model for structured responses
            
        Returns:
            Created MistralAgent instance
        """
        log_agent_action(f"Creating agent '{name}'", f"ID: {agent_id}, Model: {model}")
        
        config = AgentConfig(
            agent_id=agent_id,
            name=name,
            model=model,
            temperature=temperature,
            description=description,
            tools=tools,
            max_tokens=max_tokens,
            response_format=response_format,
            response_model=response_model
        )
        
        agent = MistralAgent(config, self.client)
        self.agents[name] = agent
        
        log_success(f"Agent '{name}' created and registered")
        return agent
    
    def get_agent(self, name: str) -> Optional[MistralAgent]:
        """
        Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            MistralAgent instance or None
        """
        agent = self.agents.get(name)
        if agent is None:
            log_warning(f"Agent '{name}' not found")
        return agent
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())
    
    def remove_agent(self, name: str) -> bool:
        """
        Remove an agent.
        
        Args:
            name: Agent name
            
        Returns:
            True if removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            log_agent_action(f"Agent '{name}' removed")
            return True
        log_warning(f"Cannot remove agent '{name}' - not found")
        return False
    
    def chat_with_retry(
        self, 
        agent_name: str, 
        message: str, 
        use_history: bool = False,
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message to an agent with automatic retry on failure (synchronous).
        
        Args:
            agent_name: Name of the agent
            message: Message to send
            use_history: Whether to use conversation history
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response
            
        Raises:
            ValueError: If agent not found
            Exception: If all retries fail
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        for attempt in range(self.max_retries):
            try:
                if use_history:
                    return agent.chat_with_history(message, stream, response_model)
                else:
                    return agent.chat(message, stream, response_model)
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    log_warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed for agent '{agent_name}'. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    log_error(f"All {self.max_retries} attempts failed for agent '{agent_name}'", e)
                    raise
    
    async def chat_with_retry_async(
        self, 
        agent_name: str, 
        message: str, 
        use_history: bool = False,
        stream: bool = False,
        response_model: Optional[Type[T]] = None
    ) -> Any:
        """
        Send a message to an agent with automatic retry on failure (asynchronous).
        
        Args:
            agent_name: Name of the agent
            message: Message to send
            use_history: Whether to use conversation history
            stream: Whether to stream the response
            response_model: Optional Pydantic model for structured response
            
        Returns:
            Agent response
            
        Raises:
            ValueError: If agent not found
            Exception: If all retries fail
        """
        agent = self.get_agent(agent_name)
        if agent is None:
            raise ValueError(f"Agent '{agent_name}' not found")
        
        for attempt in range(self.max_retries):
            try:
                if use_history:
                    return await agent.chat_with_history_async(message, stream, response_model)
                else:
                    return await agent.chat_async(message, stream, response_model)
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    log_warning(
                        f"[ASYNC] Attempt {attempt + 1}/{self.max_retries} failed for agent '{agent_name}'. "
                        f"Retrying in {self.retry_delay}s..."
                    )
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    log_error(f"[ASYNC] All {self.max_retries} attempts failed for agent '{agent_name}'", e)
                    raise
    
    async def chat_multiple_agents_async(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Send messages to multiple agents concurrently.
        
        Args:
            requests: List of dictionaries with keys:
                - agent_name: str
                - message: str
                - use_history: bool (optional, default False)
                - stream: bool (optional, default False)
                - response_model: Type[BaseModel] (optional)
                
        Returns:
            List of responses in the same order as requests
            
        Example:
            responses = await manager.chat_multiple_agents_async([
                {"agent_name": "Agent1", "message": "Hello"},
                {"agent_name": "Agent2", "message": "Hi", "use_history": True}
            ])
        """
        log_agent_action("Parallel chat", f"Sending {len(requests)} requests concurrently")
        
        tasks = []
        for req in requests:
            agent_name = req["agent_name"]
            message = req["message"]
            use_history = req.get("use_history", False)
            stream = req.get("stream", False)
            response_model = req.get("response_model")
            
            task = self.chat_with_retry_async(
                agent_name=agent_name,
                message=message,
                use_history=use_history,
                stream=stream,
                response_model=response_model
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        log_success(f"Parallel chat completed: {success_count}/{len(requests)} successful")
        
        return results
    
    def get_all_agents_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all agents."""
        return {name: agent.get_info() for name, agent in self.agents.items()}
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client is not None:
            log_agent_action("Closing Mistral client")
            # Mistral client cleanup if needed
        logger.info(f"AgentManager closed. Total agents created: {len(self.agents)}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client is not None:
            log_agent_action("Closing Mistral client (async)")
        logger.info(f"AgentManager closed (async). Total agents created: {len(self.agents)}")


# Convenience function for quick agent creation
def create_quick_agent(agent_id: str, name: str = "QuickAgent") -> MistralAgent:
    """
    Quickly create a single agent without manager.
    
    Args:
        agent_id: Mistral agent ID
        name: Agent name
        
    Returns:
        MistralAgent instance
    """
    manager = AgentManager()
    return manager.create_agent(agent_id, name)